import asyncio
import os
import uuid
from datetime import datetime
from typing import List, Optional, cast

from llama_index.core.agent.function_calling.step import (
    build_error_tool_output,
    build_missing_tool_message,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.llms.llm import ToolSelection
from llama_index.core.tools.types import BaseTool, ToolOutput
from llama_index.core.tools.calling import acall_tool_with_selection
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from agent import get_tools
from agent_factory import get_llm
from config import settings
from prompts import (
    RESUMING_PROMPT_TEMPLATE,
    STARTING_PROMPT_TEMPLATE,
    RichPromptTemplate,
)

MAX_FUNCTION_CALLS = 5
ALLOW_PARALLEL_TOOL_CALLS = True


class LoopEvent(Event):
    query: str


class ThoughtEvent(Event):
    thought: str


class ToolCallEvent(Event):
    tool_name: str
    tool_kwargs: dict


def _extract_thinking_delta(chunk: object) -> Optional[str]:
    raw = getattr(chunk, "raw", None)
    choices = getattr(raw, "choices", None) if raw else None
    if choices:
        delta = getattr(choices[0], "delta", None)
        reasoning = getattr(delta, "reasoning", None) if delta else None
        if reasoning:
            return reasoning
        content = getattr(delta, "content", None) if delta else None
        if content:
            return content

    delta = getattr(chunk, "delta", None)
    return delta if delta else None


def _build_missing_tool_output(tool_call: ToolSelection) -> ToolOutput:
    message = build_missing_tool_message(tool_call.tool_name)
    return build_error_tool_output(tool_call.tool_name, tool_call.tool_kwargs, message)


async def _call_tools(
    tool_calls: List[ToolSelection],
    tools: List[BaseTool],
) -> List[ToolOutput]:
    tools_by_name = {tool.metadata.name: tool for tool in tools}
    results: List[Optional[ToolOutput]] = [None] * len(tool_calls)
    tasks: List[asyncio.Task[ToolOutput]] = []
    task_indexes: List[int] = []

    for index, tool_call in enumerate(tool_calls):
        tool = tools_by_name.get(tool_call.tool_name)
        if tool is None:
            results[index] = _build_missing_tool_output(tool_call)
            continue

        if ALLOW_PARALLEL_TOOL_CALLS:
            task_indexes.append(index)
            tasks.append(
                asyncio.create_task(
                    acall_tool_with_selection(tool_call, tools, verbose=False)
                )
            )
        else:
            results[index] = await acall_tool_with_selection(
                tool_call, tools, verbose=False
            )

    if tasks:
        outputs = await asyncio.gather(*tasks)
        for index, output in zip(task_indexes, outputs):
            results[index] = output

    if any(output is None for output in results):
        raise RuntimeError("Tool execution did not return outputs for all tool calls.")

    return cast(List[ToolOutput], results)


class InfiniteAgentWorkflow(Workflow):
    @step
    async def start(self, ctx: Context, ev: StartEvent) -> LoopEvent:
        query = ev.get("query")
        session_id = await ctx.get("session_id", default=None)
        if not session_id:
            session_id = str(uuid.uuid4())
            await ctx.set("session_id", session_id)

        # Store the original user query for later history update
        await ctx.set("current_user_query", query)

        prompt = RichPromptTemplate(STARTING_PROMPT_TEMPLATE)
        formatted_query = prompt.format(
            query=query,
            step_threshold=settings.step_threshold,
            work_dir=os.getcwd(),
            current_pid=os.getpid(),
            current_date=datetime.now().strftime("%A, %B %d, %Y"),
        )

        await ctx.set("continuation_number", 0)
        return LoopEvent(query=formatted_query)

    @step
    async def loop(self, ctx: Context, ev: LoopEvent) -> StopEvent | LoopEvent:
        query = ev.query
        session_id = await ctx.get("session_id")

        llm = get_llm()
        tools = get_tools(ctx, session_id)

        history_dicts = await ctx.get("chat_history", default=[])
        chat_history = [
            ChatMessage(role=d["role"], content=d["content"]) for d in history_dicts
        ]

        messages = list(chat_history)
        user_msg: Optional[str] = query
        response_message: Optional[ChatMessage] = None
        function_calls = 0

        while True:
            stream = await llm.astream_chat_with_tools(
                tools=tools,
                user_msg=user_msg,
                chat_history=messages,
                verbose=False,
                allow_parallel_tool_calls=ALLOW_PARALLEL_TOOL_CALLS,
            )

            last_response = None
            async for chunk in stream:
                last_response = chunk
                thinking_delta = _extract_thinking_delta(chunk)
                if thinking_delta:
                    ctx.write_event_to_stream(ThoughtEvent(thought=thinking_delta))

            if last_response is None:
                response_message = ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content="",
                )
                break

            response_message = last_response.message
            messages.append(response_message)

            tool_calls = llm.get_tool_calls_from_response(
                last_response, error_on_no_tool_call=False
            )
            if not tool_calls or function_calls >= MAX_FUNCTION_CALLS:
                break

            if not ALLOW_PARALLEL_TOOL_CALLS and len(tool_calls) > 1:
                raise ValueError(
                    "Parallel tool calls not supported for workflow tool execution."
                )

            for tool_call in tool_calls:
                ctx.write_event_to_stream(
                    ToolCallEvent(
                        tool_name=tool_call.tool_name,
                        tool_kwargs=tool_call.tool_kwargs,
                    )
                )

            tool_outputs = await _call_tools(tool_calls, tools)
            function_calls += len(tool_calls)

            if len(tool_calls) == 1:
                tool = next(
                    (t for t in tools if t.metadata.name == tool_calls[0].tool_name),
                    None,
                )
                if tool is not None and tool.metadata.return_direct:
                    response_message = ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=tool_outputs[0].content,
                    )
                    break

            for tool_call, tool_output in zip(tool_calls, tool_outputs):
                tool_message = ChatMessage(
                    content=str(tool_output),
                    role=MessageRole.TOOL,
                    additional_kwargs={
                        "name": tool_call.tool_name,
                        "tool_call_id": tool_call.tool_id,
                    },
                )
                messages.append(tool_message)

            user_msg = None

        continue_task_flag = await ctx.get("continue_task", default=False)

        if continue_task_flag:
            summary = await ctx.get("session_summary", default="")

            continuation_number = await ctx.get("continuation_number", default=0) + 1
            await ctx.set("continuation_number", continuation_number)

            prompt = RichPromptTemplate(RESUMING_PROMPT_TEMPLATE)
            next_query = prompt.format(
                progress_text=summary,
                continuation_number=continuation_number,
                current_date=datetime.now().strftime("%A, %B %d, %Y"),
            )

            await ctx.set("continue_task", False)
            return LoopEvent(query=next_query)

        response_text = ""
        if response_message is not None and response_message.content is not None:
            response_text = str(response_message.content)

        current_query = await ctx.get("current_user_query")
        history_dicts.append({"role": MessageRole.USER, "content": current_query})
        history_dicts.append({"role": MessageRole.ASSISTANT, "content": response_text})
        await ctx.set("chat_history", history_dicts)

        return StopEvent(result=response_text)
