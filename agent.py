import os
import uuid
from datetime import datetime
from typing import List

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from agent_factory import create_agent, get_llm
from config import settings
from prompts import (
    RESUMING_PROMPT_TEMPLATE,
    STARTING_PROMPT_TEMPLATE,
    RichPromptTemplate,
)
from tools.execute_python import execute_python
from tools.finance import get_stock_data, get_stock_history
from tools.finish import get_finish_tool
from tools.subagent import call_subagent
from tools.web_scrape import web_scrape
from tools.web_search import web_search


class LoopEvent(Event):
    query: str


def get_tools(
    ctx: Context = None, session_id: str = None, include_subagent: bool = True
) -> List[FunctionTool]:
    """Returns the list of tools available to the agent."""
    tools = [
        FunctionTool.from_defaults(fn=web_search),
        FunctionTool.from_defaults(async_fn=web_scrape),
        FunctionTool.from_defaults(fn=get_stock_data),
        FunctionTool.from_defaults(fn=get_stock_history),
        FunctionTool.from_defaults(fn=execute_python),
    ]

    if ctx and session_id:
        tools.append(get_finish_tool(ctx, session_id))

    if include_subagent:
        tools.append(FunctionTool.from_defaults(async_fn=call_subagent))

    return tools


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

        # Retrieve and reconstruct chat history from context
        history_dicts = await ctx.get("chat_history", default=[])
        chat_history = [
            ChatMessage(role=d["role"], content=d["content"]) for d in history_dicts
        ]

        agent = create_agent(llm, tools=tools, chat_history=chat_history)

        response = await agent.achat(query)

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

        # Workflow is finishing, update chat history with this turn
        current_query = await ctx.get("current_user_query")
        # We append the clean user query and assistant response to history
        history_dicts.append({"role": MessageRole.USER, "content": current_query})
        history_dicts.append({"role": MessageRole.ASSISTANT, "content": str(response)})
        await ctx.set("chat_history", history_dicts)

        return StopEvent(result=str(response))


def get_agent() -> ReActAgent:
    llm = get_llm()
    tools = get_tools()
    return create_agent(llm, tools=tools)
