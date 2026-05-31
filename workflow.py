import asyncio
import json
import os
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List

import litellm
from pydantic import BaseModel

from agent import get_tools
from agent_factory import get_completion_args
from config import settings
from prompts import (
    STARTING_PROMPT_TEMPLATE,
    TITLE_SUMMARIZER_PROMPT_TEMPLATE,
    RichPromptTemplate,
)
from storage import chat_storage

logger = logging.getLogger(__name__)

MAX_FUNCTION_CALLS = 10


class ThoughtEvent(BaseModel):
    thought: str


class ContentEvent(BaseModel):
    content: str


class TitleEvent(BaseModel):
    title: str


class ToolCallEvent(BaseModel):
    tool_name: str
    tool_kwargs: dict


class AgentExecutor:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state: Dict[str, Any] = {}
        self.tools = get_tools()
        self.tool_map = {tool.__name__: tool for tool in self.tools}
        self.litellm_tools = [
            {"type": "function", "function": litellm.utils.function_to_dict(tool)}
            for tool in self.tools
        ]

    async def _load_state(self):
        self.state = await chat_storage.load_context(self.session_id)
        if not self.state:
            self.state = {
                "chat_history": [],
                "metadata": {"session_id": self.session_id},
            }

    async def _save_state(self):
        await chat_storage.save_context(self.session_id, self.state)

    async def _generate_title(self, query: str):
        existing_title = await chat_storage.get_title(self.session_id)
        if existing_title:
            logger.info(f"Using existing title for session {self.session_id}: {existing_title}")
            return existing_title

        try:
            logger.info(f"Generating new title for session {self.session_id}...")
            title_prompt = TITLE_SUMMARIZER_PROMPT_TEMPLATE.format(query=query)
            args = get_completion_args(model=settings.title_model)
            args["extra_body"] = {"enable_thinking": False}
            args["max_tokens"] = 20

            response = await litellm.acompletion(
                **args,
                messages=[{"role": "user", "content": title_prompt}],
            )
            title = response.choices[0].message.content.strip().replace('"', "")
            await chat_storage.save_title(self.session_id, title)
            logger.info(f"Generated title for session {self.session_id}: {title}")
            return title
        except Exception:
            logger.exception(f"Failed to generate title for session {self.session_id}")
            return None

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> AsyncGenerator[ToolCallEvent, None]:
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_args = json.loads(tc["function"]["arguments"])

            yield ToolCallEvent(tool_name=tool_name, tool_kwargs=tool_args)

            tool_fn = self.tool_map.get(tool_name)
            if not tool_fn:
                result = f"Tool {tool_name} not found."
            else:
                try:
                    import inspect
                    if inspect.iscoroutinefunction(tool_fn):
                        result = await tool_fn(**tool_args)
                    else:
                        result = tool_fn(**tool_args)
                except Exception as e:
                    logger.exception(f"Error executing tool {tool_name}")
                    result = f"Error executing tool {tool_name}: {e}"

            self.state["chat_history"].append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": tool_name,
                "content": str(result),
            })

    async def run(self, query: str, model_name: str) -> AsyncGenerator[Any, None]:
        await self._load_state()

        title_task = asyncio.create_task(self._generate_title(query))
        title_yielded = False

        prompt_tmpl = RichPromptTemplate(STARTING_PROMPT_TEMPLATE)
        formatted_query = prompt_tmpl.format(
            query=query,
            work_dir=os.getcwd(),
            current_pid=os.getpid(),
            current_date=datetime.now().strftime("%A, %B %d, %Y"),
        )
        self.state["current_user_query"] = query
        self.state["chat_history"].append({"role": "user", "content": formatted_query})

        completion_args = get_completion_args(model=model_name)
        function_calls = 0
        final_response_content = ""

        while function_calls < MAX_FUNCTION_CALLS:
            response = await litellm.acompletion(
                **completion_args,
                messages=self.state["chat_history"],
                tools=self.litellm_tools,
                stream=True,
            )

            current_content, current_thought, tool_calls = "", "", []

            async for chunk in response:
                delta = chunk.choices[0].delta

                if not title_yielded and title_task.done():
                    title_yielded = True
                    if title := title_task.result():
                        yield TitleEvent(title=title)

                thought = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
                if thought:
                    current_thought += thought
                    yield ThoughtEvent(thought=thought)

                if delta.content:
                    current_content += delta.content
                    yield ContentEvent(content=delta.content)

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if len(tool_calls) <= tc_delta.index:
                            tool_calls.append({
                                "id": tc_delta.id,
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            })

                        tc = tool_calls[tc_delta.index]
                        if tc_delta.id: tc["id"] = tc_delta.id
                        if tc_delta.function.name: tc["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments: tc["function"]["arguments"] += tc_delta.function.arguments

            assistant_msg = {"role": "assistant", "content": current_content}
            if current_thought: assistant_msg["thought"] = current_thought
            if tool_calls: assistant_msg["tool_calls"] = tool_calls

            self.state["chat_history"].append(assistant_msg)
            final_response_content = current_content

            if not tool_calls:
                break

            if not title_yielded and title_task.done():
                title_yielded = True
                if title := title_task.result():
                    yield TitleEvent(title=title)

            async for event in self._execute_tool_calls(tool_calls):
                yield event
                function_calls += 1

        if "current_user_query" in self.state:
            for msg in reversed(self.state["chat_history"]):
                if msg["role"] == "user":
                    msg["content"] = self.state["current_user_query"]
                    break
            del self.state["current_user_query"]

        if not title_yielded:
            if title := await title_task:
                yield TitleEvent(title=title)

        await self._save_state()
        yield final_response_content

    async def get_history(self) -> List[Dict[str, Any]]:
        await self._load_state()
        history = []
        for msg in self.state.get("chat_history", []):
            if msg["role"] == "tool":
                continue

            item = {
                "role": msg["role"],
                "content": msg.get("content", ""),
                "thought": msg.get("thought") or None,
            }
            if msg["role"] == "assistant" and (tcs := msg.get("tool_calls")):
                item["tool_calls"] = [{"name": tc["function"]["name"]} for tc in tcs]
            history.append(item)
        return history
