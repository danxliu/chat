import asyncio
import base64
import json
import logging
import time
from datetime import datetime
from typing import Any, AsyncGenerator

from pydantic import BaseModel
from pypdf import PdfReader

from agent import execute_tool, get_tools_schema
from config import settings
from llm import get_completion_args, openai_client
from memory import MemoryManager
from models import Attachment, Block, ChatMessage, Metrics, get_model_context_limit
from prompts import (
    COMPACTION_PROMPT,
    STARTING_PROMPT_TEMPLATE,
)
from storage import chat_storage

logger = logging.getLogger(__name__)


class ThoughtEvent(BaseModel):
    thought: str


class ContentEvent(BaseModel):
    content: str
    block_index: int


class ToolCallFunction(BaseModel):
    name: str = ""
    arguments: str = ""


class ToolCall(BaseModel):
    id: str | None = None
    type: str = "function"
    function: ToolCallFunction


class ToolCallEvent(BaseModel):
    tool_name: str
    tool_kwargs: dict


class RichBlockEvent(BaseModel):
    block: Block


class ErrorEvent(BaseModel):
    error: str


class WarningEvent(BaseModel):
    warning: str


class FinalResponseEvent(BaseModel):
    content: str
    metrics: dict[str, Any] | None = None


class TokenUsageEvent(BaseModel):
    current_tokens: int
    max_tokens: int


def build_rich_block(tool_name: str, args: dict, index: int) -> Block | None:
    if tool_name == "draw_chart":
        return Block(index=index, type="chart", content=args)
    if tool_name == "suggest_continuations":
        return Block(index=index, type="continuations", content=args)
    return None


class AgentExecutor:
    def __init__(self, session_id: str, user_id: str | None = None):
        self.session_id = session_id
        self.user_id = user_id or MemoryManager.DEFAULT_USER_ID
        self.memory = MemoryManager(user_id=self.user_id)
        self.state: dict[str, Any] = {}

    async def _load_state(self):
        state = await chat_storage.load_context(self.user_id, self.session_id)
        defaults = {
            "chat_history": [],
            "metadata": {"session_id": self.session_id},
            "compacted_summary": None,
            "summarized_until_index": 0,
            "last_prompt_tokens": 0,
        }
        if state:
            for key, val in defaults.items():
                state.setdefault(key, val)
            self.state = state
        else:
            self.state = defaults

    async def _save_state(self):
        await chat_storage.save_context(self.user_id, self.session_id, self.state)

    def _process_attachments(
        self, attachments: list[dict] | None
    ) -> tuple[list[dict], str]:
        processed_attachments = []
        extra_content = ""

        if not attachments:
            return processed_attachments, extra_content

        for att in attachments:
            filename = att.get("filename")
            mime_type = att.get("mime_type", "")
            stored_filename = att.get("stored_filename")

            if not stored_filename:
                continue

            file_path = settings.UPLOADS_DIR / stored_filename
            if not file_path.exists():
                continue

            if mime_type.startswith("image/"):
                base64_data = base64.b64encode(file_path.read_bytes()).decode()
                processed_attachments.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_data}"},
                    }
                )
            elif mime_type == "application/pdf":
                try:
                    reader = PdfReader(file_path)
                    text = "".join(page.extract_text() + "\n" for page in reader.pages)
                    extra_content += f"\n\n--- Content of {filename} ---\n{text}\n"
                except Exception as e:
                    logger.error(f"Error reading PDF {filename}: {e}")
                    extra_content += f"\n\nError reading PDF {filename}: {e}\n"
            else:
                try:
                    text = file_path.read_text(encoding="utf-8")
                    extra_content += f"\n\n--- Content of {filename} ---\n{text}\n"
                except Exception as e:
                    logger.error(f"Error reading text file {filename}: {e}")
                    extra_content += f"\n\nError reading file {filename}: {e}\n"

        return processed_attachments, extra_content

    async def run(
        self,
        query: str,
        model_name: str,
        attachments: list[dict] | None = None,
        enable_reasoning: bool = True,
    ) -> AsyncGenerator[Any, None]:
        await self._load_state()

        processed_attachments, extra_content = self._process_attachments(attachments)

        full_query = query + extra_content
        self.state["chat_history"].append(
            {"role": "user", "content": query, "attachments": attachments}
        )
        await self._save_state()

        # Check if auto-compaction is needed before this turn
        if self._needs_compaction():
            logger.info(
                "Triggering compaction for session %s (prompt_tokens=%d, limit=%d)",
                self.session_id,
                self.state.get("last_prompt_tokens", 0),
                settings.max_context_tokens,
            )
            await self._compact()
            await self._save_state()

        # Retrieve relevant cross-session memories
        memory_context = await self.memory.retrieve(full_query)

        formatted_query_text = STARTING_PROMPT_TEMPLATE.format(
            query=full_query,
            current_date=datetime.now().strftime("%A, %B %d, %Y"),
            memory_context=memory_context or "(No prior memories yet.)",
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
        total_prompt_tokens = 0
        block_index = 0
        current_text_block_active = False

        try:
            while not should_stop:
                api_messages = self._build_api_messages(user_content)

                response = await openai_client.chat.completions.create(
                    **completion_args,
                    messages=api_messages,
                    stream=True,
                )

                current_content, current_thought = "", ""
                tool_calls: list[ToolCall] = []

                try:
                    async for chunk in response:
                        if chunk.usage:
                            total_completion_tokens += chunk.usage.completion_tokens
                            if chunk.usage.prompt_tokens:
                                total_prompt_tokens = chunk.usage.prompt_tokens

                        if not chunk.choices:
                            continue

                        delta = chunk.choices[0].delta

                        # Handle Thinking
                        thought = getattr(delta, "reasoning_content", None) or getattr(
                            delta, "reasoning", None
                        )
                        if thought is None:
                            extra = getattr(delta, "model_extra", None) or {}
                            thought = extra.get("reasoning_content") or extra.get(
                                "reasoning"
                            )
                        if thought:
                            current_thought += thought
                            yield ThoughtEvent(thought=thought)

                        # Handle Content
                        if delta.content:
                            current_content += delta.content
                            if not current_text_block_active:
                                current_text_block_active = True
                            yield ContentEvent(
                                content=delta.content, block_index=block_index
                            )

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
                    if current_text_block_active:
                        block_index += 1
                        current_text_block_active = False

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

                        block = build_rich_block(name, args, block_index)
                        if block:
                            yield RichBlockEvent(block=block)
                            block_index += 1
                        else:
                            yield ToolCallEvent(tool_name=name, tool_kwargs=args)

                        result = await execute_tool(name, args)
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

                    # Update prompt token tracking for compaction decisions
                    if total_prompt_tokens > 0:
                        self.state["last_prompt_tokens"] = total_prompt_tokens
                    else:
                        # Fallback: estimate from message content lengths (~4 chars/token)
                        self.state["last_prompt_tokens"] = self._estimate_prompt_tokens()
                    await self._save_state()

                    # Fire-and-forget: extract memories from this exchange
                    asyncio.create_task(
                        self.memory.extract_and_store(query, final_content)
                    )

                    max_ctx = get_model_context_limit(model_name)
                    yield TokenUsageEvent(
                        current_tokens=self.state["last_prompt_tokens"],
                        max_tokens=max_ctx,
                    )
                    yield FinalResponseEvent(content=final_content, metrics=metrics)
                    return

        except Exception as e:
            logger.exception("Critical error during agent execution.")
            yield ErrorEvent(error=str(e))
        finally:
            await self._save_state()

    async def _compact(self) -> None:
        """Summarize older messages into a rolling compaction summary,
        keeping only the most recent messages in full for the LLM context."""
        keep_recent = settings.compaction_keep_recent
        history = self.state["chat_history"]
        start_idx = self.state.get("summarized_until_index", 0)
        end_idx = max(start_idx, len(history) - keep_recent)

        if end_idx <= start_idx:
            return

        segment = history[start_idx:end_idx]
        existing = self.state.get("compacted_summary") or ""

        # Build a text representation of the segment to summarize
        lines = []
        for msg in segment:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "tool":
                name = msg.get("name", "tool")
                content = f"[{name} result]: {str(content)[:settings.compaction_tool_result_max_chars]}"
                lines.append(f"Tool ({name}): {content}")
            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    tc_names = [tc.get("function", {}).get("name", "?") for tc in tool_calls]
                    content = f"[Called tools: {', '.join(tc_names)}] {content}"
                lines.append(f"Assistant: {content}")
            elif role == "user":
                lines.append(f"User: {content}")

        segment_text = "\n".join(lines)
        if not segment_text.strip():
            return

        prompt = COMPACTION_PROMPT.format(
            existing=existing or "(No prior summary)",
            segment_text=segment_text,
        )

        try:
            completion_args = get_completion_args(model=settings.compaction_model)
            completion_args["temperature"] = settings.compaction_temperature
            completion_args["max_tokens"] = settings.compaction_max_tokens
            response = await openai_client.chat.completions.create(
                **completion_args,
                messages=[{"role": "user", "content": prompt}],
            )
            new_summary = response.choices[0].message.content or ""
            if new_summary.strip():
                self.state["compacted_summary"] = new_summary.strip()
            self.state["summarized_until_index"] = end_idx
            logger.info(
                "Compacted %d messages (indices %d-%d) for session %s",
                len(segment), start_idx, end_idx - 1, self.session_id,
            )
        except Exception:
            logger.exception("Compaction summarization failed for session %s", self.session_id)

    def _needs_compaction(self) -> bool:
        """Check whether the conversation context is approaching the limit."""
        threshold = int(settings.max_context_tokens * settings.compaction_trigger_pct)
        last_tokens = self.state.get("last_prompt_tokens", 0)
        if last_tokens == 0:
            return False
        return last_tokens >= threshold

    def _estimate_prompt_tokens(self) -> int:
        """Rough token count from message content as fallback when the API
        doesn't report prompt_tokens. Uses ~4 chars per token (conservative)."""
        total = 0
        for msg in self.state.get("chat_history", []):
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            total += len(str(content))
        return max(1, total // 4)

    def _build_api_messages(
        self, user_content: str | list[dict]
    ) -> list[dict[str, Any]]:
        """Build the list of messages to send to the LLM, optionally compacted."""
        history = self.state["chat_history"]
        summarized_until = self.state.get("summarized_until_index", 0)
        compacted_summary = self.state.get("compacted_summary")

        api_messages: list[dict[str, Any]] = []
        if compacted_summary and summarized_until > 0:
            api_messages.append(
                {
                    "role": "system",
                    "content": (
                        "[The following is a summary of the earlier conversation, "
                        "provided so you can continue without losing context.]\n\n"
                        f"{compacted_summary}"
                    ),
                }
            )
            history = history[summarized_until:]

        for msg in history:
            cleaned = {"role": msg["role"]}
            if "content" in msg:
                cleaned["content"] = msg["content"]
            if "tool_calls" in msg:
                cleaned["tool_calls"] = msg["tool_calls"]
            if "tool_call_id" in msg:
                cleaned["tool_call_id"] = msg["tool_call_id"]
            if "name" in msg:
                cleaned["name"] = msg["name"]
            api_messages.append(cleaned)
        for i in reversed(range(len(api_messages))):
            if api_messages[i]["role"] == "user":
                api_messages[i]["content"] = user_content
                break

        return api_messages

    async def get_history(self) -> list[ChatMessage]:
        await self._load_state()
        history: list[ChatMessage] = []

        for msg in self.state.get("chat_history", []):
            role = msg.get("role")
            if role == "user":
                history.append(
                    ChatMessage(
                        role="user",
                        blocks=[
                            Block(index=0, type="text", content=msg.get("content", ""))
                        ],
                        attachments=msg.get("attachments"),
                    )
                )
            elif role == "assistant":
                if history and history[-1].role == "assistant":
                    target = history[-1]
                else:
                    target = ChatMessage(role="assistant", blocks=[])
                    history.append(target)

                block_index = len(target.blocks)

                new_thought = msg.get("thought", "")
                for tc in msg.get("tool_calls", []):
                    name = tc.get("function", {}).get("name", "unknown")
                    new_thought += f"\n\n**Tool Call:** {name}\n\n"

                if new_thought:
                    target.thought = (target.thought or "") + new_thought

                new_content = msg.get("content", "")
                if new_content:
                    if target.blocks and target.blocks[-1].type == "text":
                        target.blocks[-1].content += "\n\n" + new_content
                    else:
                        target.blocks.append(
                            Block(index=block_index, type="text", content=new_content)
                        )
                        block_index += 1

                for tc in msg.get("tool_calls", []):
                    name = tc.get("function", {}).get("name", "unknown")
                    args_str = tc.get("function", {}).get("arguments", "{}")
                    try:
                        args = json.loads(args_str) if args_str else {}
                    except json.JSONDecodeError:
                        args = {}

                    block = build_rich_block(name, args, block_index)
                    if block:
                        target.blocks.append(block)
                        block_index += 1

                if msg.get("metrics"):
                    target.metrics = Metrics(**msg["metrics"])
                if msg.get("attachments"):
                    target.attachments = [Attachment(**a) for a in msg["attachments"]]

        return history
