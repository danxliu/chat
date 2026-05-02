import os
import tempfile
import uuid
from datetime import datetime
from typing import List

import yaml
from llama_index.core.agent import AgentRunner, FunctionCallingAgentWorker
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from llama_index.llms.openai_like import OpenAILike

from config import settings
from prompts import STARTING_PROMPT_TEMPLATE, RESUMING_PROMPT_TEMPLATE, RichPromptTemplate
from tools.finish import get_finish_tool
from tools.web_search import web_search
from tools.web_scrape import web_scrape
from tools.finance import get_stock_data, get_stock_history
from tools.execute_python import execute_python
from tools.ask_user import ask_user
from tools.trading import get_account_info, get_positions, place_order, get_tickers


class LoopEvent(Event):
    query: str


def get_llm() -> OpenAILike:
    """Configures the LLM to connect to the local OpenAI-compatible endpoint."""
    return OpenAILike(
        api_base=settings.api_base,
        api_key=settings.api_key,
        model=settings.model,
        is_function_calling_model=True,
        is_chat_model=True,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        timeout=settings.timeout,
    )


def create_agent(llm: OpenAILike, tools: List[FunctionTool]) -> AgentRunner:
    """Creates the agent worker and wraps it in a runner loop."""
    agent_worker = FunctionCallingAgentWorker.from_tools(tools, llm=llm, verbose=True)
    return AgentRunner(agent_worker)


def _get_session_state(session_id: str) -> dict:
    """Helper to read the session state from the temporary YAML file."""
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"agent_session_{session_id}.yaml")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


class InfiniteAgentWorkflow(Workflow):
    @step
    async def start(self, ctx: Context, ev: StartEvent) -> LoopEvent:
        query = ev.get("query")
        session_id = await ctx.get("session_id", default=None)
        if not session_id:
            session_id = str(uuid.uuid4())
            await ctx.set("session_id", session_id)
            
        prompt = RichPromptTemplate(STARTING_PROMPT_TEMPLATE)
        formatted_query = prompt.format(
            query=query,
            step_threshold=settings.step_threshold,
            work_dir=os.getcwd(),
            current_pid=os.getpid(),
            current_date=datetime.now().strftime("%A, %B %d, %Y")
        )
        
        await ctx.set("continuation_number", 0)
        return LoopEvent(query=formatted_query)

    @step
    async def loop(self, ctx: Context, ev: LoopEvent) -> StopEvent | LoopEvent:
        query = ev.query
        session_id = await ctx.get("session_id")

        llm = get_llm()
        finish_tool = get_finish_tool(ctx, session_id)
        
        web_search_tool = FunctionTool.from_defaults(fn=web_search)
        web_scrape_tool = FunctionTool.from_defaults(fn=web_scrape)
        get_stock_data_tool = FunctionTool.from_defaults(fn=get_stock_data)
        get_stock_history_tool = FunctionTool.from_defaults(fn=get_stock_history)
        execute_python_tool = FunctionTool.from_defaults(fn=execute_python)
        ask_user_tool = FunctionTool.from_defaults(fn=ask_user)
        get_account_info_tool = FunctionTool.from_defaults(fn=get_account_info)
        get_positions_tool = FunctionTool.from_defaults(fn=get_positions)
        place_order_tool = FunctionTool.from_defaults(fn=place_order)
        get_tickers_tool = FunctionTool.from_defaults(fn=get_tickers)

        agent = create_agent(llm, tools=[
            finish_tool,
            web_search_tool,
            web_scrape_tool,
            get_stock_data_tool,
            get_stock_history_tool,
            execute_python_tool,
            ask_user_tool,
            get_account_info_tool,
            get_positions_tool,
            place_order_tool,
            get_tickers_tool
        ])

        response = await agent.achat(query)

        continue_task_flag = await ctx.get("continue_task", default=False)

        if continue_task_flag:
            state = _get_session_state(session_id)
            summary = state.get("summary", "")
            
            continuation_number = await ctx.get("continuation_number", default=0) + 1
            await ctx.set("continuation_number", continuation_number)
            
            prompt = RichPromptTemplate(RESUMING_PROMPT_TEMPLATE)
            next_query = prompt.format(
                progress_text=summary,
                continuation_number=continuation_number,
                current_date=datetime.now().strftime("%A, %B %d, %Y")
            )
            
            await ctx.set("continue_task", False)
            return LoopEvent(query=next_query)
        return StopEvent(result=str(response))


def get_agent() -> AgentRunner:
    """Convenience function to initialize and return the fully configured agent."""
    llm = get_llm()
    
    web_search_tool = FunctionTool.from_defaults(fn=web_search)
    web_scrape_tool = FunctionTool.from_defaults(fn=web_scrape)
    get_stock_data_tool = FunctionTool.from_defaults(fn=get_stock_data)
    get_stock_history_tool = FunctionTool.from_defaults(fn=get_stock_history)
    execute_python_tool = FunctionTool.from_defaults(fn=execute_python)
    ask_user_tool = FunctionTool.from_defaults(fn=ask_user)
    get_account_info_tool = FunctionTool.from_defaults(fn=get_account_info)
    get_positions_tool = FunctionTool.from_defaults(fn=get_positions)
    place_order_tool = FunctionTool.from_defaults(fn=place_order)
    get_tickers_tool = FunctionTool.from_defaults(fn=get_tickers)

    return create_agent(llm, tools=[
        web_search_tool,
        web_scrape_tool,
        get_stock_data_tool,
        get_stock_history_tool,
        execute_python_tool,
        ask_user_tool,
        get_account_info_tool,
        get_positions_tool,
        place_order_tool,
        get_tickers_tool
    ])
