import json
import logging
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

import litellm
from pydantic import BaseModel

from agent import execute_tool, get_completion_args, get_tools_schema
from config import settings
from memory import add_memory, search_memories
from prompts import (
    STARTING_PROMPT_TEMPLATE,
    TITLE_SUMMARIZER_PROMPT_TEMPLATE,
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


class FinalResponseEvent(BaseModel):
    content: str


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
            title_prompt = TITLE_SUMMARIZER_PROMPT_TEMPLATE.format(query=query)
            args = get_completion_args(model=settings.title_model)
            response = await litellm.acompletion(
                **args,
                messages=[{"role": "user", "content": title_prompt}],
                max_tokens=20,
                temperature=0.3,
            )
            title = response.choices[0].message.content.strip().replace('"', "")
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

    async def run(self, query: str, model_name: str) -> AsyncGenerator[Any, None]:
        await self._load_state()
        self.state["chat_history"].append({"role": "user", "content": query})
        await self._save_state()

        # Fetch relevant memories
        memories = search_memories(query)
        memory_str = (
            "\n".join(f"- {m}" for m in memories)
            if memories
            else "No previous memories found."
        )

        formatted_query = STARTING_PROMPT_TEMPLATE.format(
            query=query,
            current_date=datetime.now().strftime("%A, %B %d, %Y"),
            memory=memory_str,
        )
        completion_args = get_completion_args(model=model_name)
        completion_args["tools"] = get_tools_schema()
        completion_args["tool_choice"] = "auto"

        final_content = ""
        should_stop = False

        try:
            while not should_stop:
                api_messages = self.state["chat_history"].copy()
                # Inject the formatted prompt into the most recent user message for the API call
                for i in reversed(range(len(api_messages))):
                    if api_messages[i]["role"] == "user":
                        api_messages[i] = {
                            **api_messages[i],
                            "content": formatted_query,
                        }
                        break

                response = await litellm.acompletion(
                    **completion_args,
                    messages=api_messages,
                    stream=True,
                )

                current_content, current_thought = "", ""
                tool_calls: List[ToolCall] = []

                async for chunk in response:
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
                                tool_calls.append(ToolCall(function=ToolCallFunction()))

                            target = tool_calls[index]
                            if tc.id:
                                target.id = tc.id
                            if tc.function.name:
                                target.function.name += tc.function.name
                            if tc.function.arguments:
                                target.function.arguments += tc.function.arguments

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
                        if name == "finish_task":
                            should_stop = True

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
                    self.state["chat_history"].append(assistant_msg)
                    # If the agent sends a message without calling a tool, we give it a reminder
                    self.state["chat_history"].append(
                        {
                            "role": "system",
                            "content": "You have not called any tools. If you have finished the task, please call the finish_task tool. If you need to perform more actions, use the available tools.",
                        }
                    )
                    await self._save_state()
                    continue

        except Exception as e:
            logger.exception("Critical error during agent execution.")
            yield ErrorEvent(error=str(e))
        finally:
            await self._save_state()
            # Store new memories from the interaction
            if final_content:
                add_memory(f"User: {query}\nAssistant: {final_content}")

        yield FinalResponseEvent(content=final_content)

    async def get_history(self) -> List[Dict[str, Any]]:
        await self._load_state()
        history = []
        for msg in self.state.get("chat_history", []):
            if msg["role"] not in ("user", "assistant"):
                continue

            item = {
                "role": msg["role"],
                "content": msg.get("content", ""),
                "thought": msg.get("thought") or None,
            }
            history.append(item)
        return history
