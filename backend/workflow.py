import base64
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import litellm
from pydantic import BaseModel
from pypdf import PdfReader

from agent import execute_tool, get_completion_args, get_tools_schema
from config import settings
from memory import add_memory, search_memories
from models import Attachment, ChatMessage, Metrics
from prompts import (
    STARTING_PROMPT_TEMPLATE,
)
from storage import chat_storage

logger = logging.getLogger(__name__)


class ThoughtEvent(BaseModel):
    thought: str


class ContentEvent(BaseModel):
    content: str


class ToolCallFunction(BaseModel):
    name: str = ""
    arguments: str = ""


class ToolCall(BaseModel):
    id: Optional[str] = None
    type: str = "function"
    function: ToolCallFunction


class ToolCallEvent(BaseModel):
    tool_name: str
    tool_kwargs: dict


class ErrorEvent(BaseModel):
    error: str


class WarningEvent(BaseModel):
    warning: str


class FinalResponseEvent(BaseModel):
    content: str
    metrics: Optional[Dict[str, Any]] = None


class AgentExecutor:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state: Dict[str, Any] = {}

    async def _load_state(self):
        self.state = await chat_storage.load_context(self.session_id)
        if not self.state:
            self.state = {
                "chat_history": [],
                "metadata": {"session_id": self.session_id},
            }

    async def _save_state(self):
        await chat_storage.save_context(self.session_id, self.state)

    async def _generate_title(self, query: str) -> Optional[str]:
        try:
            logger.info(f"Generating new title for session {self.session_id}...")
            title = (query[:50] + "...") if len(query) > 50 else query
            await chat_storage.save_title(self.session_id, title)
            logger.info(f"Generated title for session {self.session_id}: {title}")
            return title
        except Exception:
            logger.exception(f"Failed to generate title for session {self.session_id}")
            return None

    async def get_title(self, query: str) -> Optional[str]:
        existing_title = await chat_storage.get_title(self.session_id)
        if existing_title:
            logger.info(
                f"Using existing title for session {self.session_id}: {existing_title}"
            )
            return existing_title
        logger.info(
            f"Generating new title for session {self.session_id} based on query: {query}"
        )
        return await self._generate_title(query)

    async def run(
        self,
        query: str,
        model_name: str,
        attachments: Optional[List[dict]] = None,
        enable_reasoning: bool = True,
    ) -> AsyncGenerator[Any, None]:
        await self._load_state()

        processed_attachments = []
        extra_content = ""

        if attachments:
            for att in attachments:
                filename = att.get("filename")
                mime_type = att.get("mime_type", "")
                stored_filename = att.get("stored_filename")

                if not stored_filename:
                    continue

                file_path = Path("uploads") / stored_filename
                if not file_path.exists():
                    continue

                if mime_type.startswith("image/"):
                    with open(file_path, "rb") as f:
                        base64_data = base64.b64encode(f.read()).decode("utf-8")
                    processed_attachments.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_data}"
                            },
                        }
                    )
                elif mime_type == "application/pdf":
                    try:
                        reader = PdfReader(file_path)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        extra_content += f"\n\n--- Content of {filename} ---\n{text}\n"
                    except Exception as e:
                        logger.error(f"Error reading PDF {filename}: {e}")
                        extra_content += f"\n\nError reading PDF {filename}: {e}\n"
                else:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            text = f.read()
                        extra_content += f"\n\n--- Content of {filename} ---\n{text}\n"
                    except Exception as e:
                        logger.error(f"Error reading text file {filename}: {e}")
                        extra_content += f"\n\nError reading file {filename}: {e}\n"

        full_query = query + extra_content
        self.state["chat_history"].append(
            {"role": "user", "content": query, "attachments": attachments}
        )
        await self._save_state()

        # Fetch relevant memories
        memories = search_memories(query)
        memory_str = (
            "\n".join(f"- {m}" for m in memories)
            if memories
            else "No previous memories found."
        )

        formatted_query_text = STARTING_PROMPT_TEMPLATE.format(
            query=full_query,
            current_date=datetime.now().strftime("%A, %B %d, %Y"),
            memory=memory_str,
        )

        # Build multi-modal message if there are images
        if processed_attachments:
            user_content = [{"type": "text", "text": formatted_query_text}]
            user_content.extend(processed_attachments)
        else:
            user_content = formatted_query_text

        completion_args = get_completion_args(model=model_name)
        completion_args["tools"] = get_tools_schema()
        completion_args["tool_choice"] = "auto"
        completion_args["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": enable_reasoning}
        }
        completion_args["stream_options"] = {"include_usage": True}

        final_content = ""
        should_stop = False
        start_time = time.time()
        total_completion_tokens = 0

        try:
            while not should_stop:
                api_messages = self.state["chat_history"].copy()
                # Inject the formatted prompt into the most recent user message for the API call
                for i in reversed(range(len(api_messages))):
                    if api_messages[i]["role"] == "user":
                        api_messages[i] = {
                            **api_messages[i],
                            "content": user_content,
                        }
                        break

                response = await litellm.acompletion(
                    **completion_args,
                    messages=api_messages,
                    stream=True,
                )

                current_content, current_thought = "", ""
                tool_calls: List[ToolCall] = []

                try:
                    async for chunk in response:
                        if hasattr(chunk, "usage") and chunk.usage:
                            usage = chunk.usage
                            tokens = getattr(usage, "completion_tokens", 0)
                            if tokens == 0 and isinstance(usage, dict):
                                tokens = usage.get("completion_tokens", 0)
                            total_completion_tokens += tokens

                        if not chunk.choices:
                            continue

                        delta = chunk.choices[0].delta

                        # Handle Thinking
                        thought = getattr(delta, "reasoning_content", None) or getattr(
                            delta, "reasoning", None
                        )
                        if thought:
                            current_thought += thought
                            yield ThoughtEvent(thought=thought)

                        # Handle Content
                        if delta.content:
                            current_content += delta.content
                            yield ContentEvent(content=delta.content)

                        # Handle Tool Calls
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                index = tc.index
                                while len(tool_calls) <= index:
                                    tool_calls.append(
                                        ToolCall(function=ToolCallFunction())
                                    )

                                target = tool_calls[index]
                                if tc.id:
                                    target.id = tc.id
                                if tc.function.name:
                                    target.function.name += tc.function.name
                                if tc.function.arguments:
                                    target.function.arguments += tc.function.arguments
                except Exception as e:
                    logger.warning(f"Stream reading interrupted: {e}")

                assistant_msg = {"role": "assistant", "content": current_content}
                if current_thought:
                    assistant_msg["thought"] = current_thought

                if current_content:
                    if final_content:
                        final_content += "\n\n" + current_content
                    else:
                        final_content = current_content

                if tool_calls:
                    tool_calls_dict = [tc.model_dump() for tc in tool_calls]
                    assistant_msg["tool_calls"] = tool_calls_dict
                    self.state["chat_history"].append(assistant_msg)

                    for tc in tool_calls:
                        name = tc.function.name

                        args_str = tc.function.arguments
                        try:
                            args = json.loads(args_str) if args_str else {}
                        except json.JSONDecodeError:
                            args = {}

                        yield ToolCallEvent(tool_name=name, tool_kwargs=args)

                        result = execute_tool(name, args)
                        self.state["chat_history"].append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "name": name,
                                "content": result,
                            }
                        )
                    await self._save_state()
                    continue
                else:
                    total_time = time.time() - start_time
                    metrics = None
                    if total_completion_tokens > 0:
                        metrics = {
                            "time_s": total_time,
                            "tokens": total_completion_tokens,
                            "tokens_per_sec": total_completion_tokens / total_time
                            if total_time > 0
                            else 0,
                        }

                    assistant_msg["metrics"] = metrics
                    self.state["chat_history"].append(assistant_msg)
                    should_stop = True
                    await self._save_state()

                    yield FinalResponseEvent(content=final_content, metrics=metrics)
                    return

        except Exception as e:
            logger.exception("Critical error during agent execution.")
            yield ErrorEvent(error=str(e))
        finally:
            await self._save_state()
            # Store new memories from the interaction
            if final_content:
                add_memory(f"User: {query}\nAssistant: {final_content}")

    async def get_history(self) -> List[ChatMessage]:
        await self._load_state()
        history: List[ChatMessage] = []

        for msg in self.state.get("chat_history", []):
            role = msg.get("role")
            if role == "user":
                history.append(
                    ChatMessage(
                        role="user",
                        content=msg.get("content", ""),
                        attachments=msg.get("attachments"),
                    )
                )
            elif role == "assistant":
                if history and history[-1].role == "assistant":
                    target = history[-1]
                else:
                    target = ChatMessage(role="assistant", content="")
                    history.append(target)

                new_thought = msg.get("thought", "")
                for tc in msg.get("tool_calls", []):
                    name = tc.get("function", {}).get("name", "unknown")
                    new_thought += f"\n\n**Tool Call:** {name}\n\n"

                if new_thought:
                    target.thought = (target.thought or "") + new_thought

                new_content = msg.get("content", "")
                if new_content:
                    target.content = (
                        f"{target.content}\n\n{new_content}"
                        if target.content
                        else new_content
                    )

                if msg.get("metrics"):
                    target.metrics = Metrics(**msg["metrics"])
                if msg.get("attachments"):
                    target.attachments = [Attachment(**a) for a in msg["attachments"]]

        return history
