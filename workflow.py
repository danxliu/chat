import asyncio
import json
import os
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
        if not existing_title:
            try:
                title_prompt = TITLE_SUMMARIZER_PROMPT_TEMPLATE.format(query=query)
                completion_args = get_completion_args()
                # Disable reasoning for title generation
                completion_args["extra_body"] = {"enable_thinking": False}

                response = await litellm.acompletion(
                    **completion_args,
                    messages=[{"role": "user", "content": title_prompt}],
                )
                title = response.choices[0].message.content.strip().replace('"', "")
                await chat_storage.save_title(self.session_id, title)
                return title
            except Exception as e:
                print(f"Failed to generate title for session {self.session_id}: {e}")
        return existing_title

    async def run(self, query: str) -> AsyncGenerator[Any, None]:
        await self._load_state()

        # Run title generation in background to not block the main loop
        title_task = asyncio.create_task(self._generate_title(query))
        title_yielded = False

        # Prepare the prompt
        prompt_tmpl = RichPromptTemplate(STARTING_PROMPT_TEMPLATE)
        formatted_query = prompt_tmpl.format(
            query=query,
            work_dir=os.getcwd(),
            current_pid=os.getpid(),
            current_date=datetime.now().strftime("%A, %B %d, %Y"),
        )
        # Store original query to replace the formatted one in history later
        self.state["current_user_query"] = query

        self.state["chat_history"].append({"role": "user", "content": formatted_query})

        completion_args = get_completion_args()
        function_calls = 0
        final_response_content = ""

        while function_calls < MAX_FUNCTION_CALLS:
            response = await litellm.acompletion(
                **completion_args,
                messages=self.state["chat_history"],
                tools=self.litellm_tools,
                stream=True,
            )

            current_content = ""
            current_thought = ""
            tool_calls = []

            async for chunk in response:
                delta = chunk.choices[0].delta

                # Handle title update if ready
                if not title_yielded and title_task.done():
                    try:
                        title = title_task.result()
                        if title:
                            yield TitleEvent(title=title)
                        title_yielded = True
                    except Exception:
                        title_yielded = True

                # Handle reasoning/thoughts
                thought = getattr(delta, "reasoning_content", None) or getattr(
                    delta, "reasoning", None
                )
                if thought:
                    current_thought += thought
                    yield ThoughtEvent(thought=thought)

                if delta.content:
                    current_content += delta.content
                    yield ContentEvent(content=delta.content)

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if len(tool_calls) <= tc_delta.index:
                            tool_calls.append(
                                {
                                    "id": tc_delta.id,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )

                        if tc_delta.id:
                            tool_calls[tc_delta.index]["id"] = tc_delta.id
                        if tc_delta.function.name:
                            tool_calls[tc_delta.index]["function"]["name"] += (
                                tc_delta.function.name
                            )
                        if tc_delta.function.arguments:
                            tool_calls[tc_delta.index]["function"]["arguments"] += (
                                tc_delta.function.arguments
                            )

            # Create assistant message for history
            assistant_msg = {"role": "assistant", "content": current_content}
            if current_thought:
                assistant_msg["thought"] = current_thought
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls

            self.state["chat_history"].append(assistant_msg)
            final_response_content = current_content

            if not tool_calls:
                break

            # Check title update after potential early break
            if not title_yielded and title_task.done():
                try:
                    title = title_task.result()
                    if title:
                        yield TitleEvent(title=title)
                    title_yielded = True
                except Exception:
                    title_yielded = True

            # Execute tool calls
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                tool_args = json.loads(tc["function"]["arguments"])

                yield ToolCallEvent(tool_name=tool_name, tool_kwargs=tool_args)

                tool_fn = self.tool_map.get(tool_name)
                if tool_fn:
                    try:
                        import inspect

                        if inspect.iscoroutinefunction(tool_fn):
                            result = await tool_fn(**tool_args)
                        else:
                            result = tool_fn(**tool_args)
                    except Exception as e:
                        result = f"Error executing tool {tool_name}: {e}"
                else:
                    result = f"Tool {tool_name} not found."

                self.state["chat_history"].append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": tool_name,
                        "content": str(result),
                    }
                )

                function_calls += 1

        # Cleanup: Replace formatted user query with original query in history for storage
        if "current_user_query" in self.state:
            for msg in reversed(self.state["chat_history"]):
                if msg["role"] == "user":
                    msg["content"] = self.state["current_user_query"]
                    break
            del self.state["current_user_query"]

        await self._save_state()
        yield final_response_content

    async def get_history(self) -> List[Dict[str, Any]]:
        await self._load_state()
        history = []
        for msg in self.state.get("chat_history", []):
            role = msg["role"]
            content = msg.get("content", "")

            # Skip tool responses from being displayed as regular messages in history
            if role == "tool":
                continue

            thought = msg.get("thought", "")

            if role in ["user", "assistant"]:
                item = {
                    "role": role,
                    "content": content,
                    "thought": thought if thought else None,
                }
                if role == "assistant" and msg.get("tool_calls"):
                    item["tool_calls"] = [
                        {"name": tc["function"]["name"]} for tc in msg["tool_calls"]
                    ]
                history.append(item)
        return history
