import os
import tempfile
import uuid
from datetime import datetime
from typing import List

import yaml
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from config import settings
from prompts import STARTING_PROMPT_TEMPLATE, RESUMING_PROMPT_TEMPLATE, RichPromptTemplate
from tools.finish import get_finish_tool
from tools.web_search import web_search
from tools.web_scrape import web_scrape
from tools.finance import get_stock_data, get_stock_history
from tools.execute_python import execute_python
from tools.ask_user import ask_user
from tools.subagent import call_subagent
from agent_factory import get_llm, create_agent

class LoopEvent(Event):
    query: str


def get_tools(ctx: Context = None, session_id: str = None, include_subagent: bool = True) -> List[FunctionTool]:
    """Returns the list of tools available to the agent."""
    tools = [
        FunctionTool.from_defaults(fn=web_search),
        FunctionTool.from_defaults(async_fn=web_scrape),
        FunctionTool.from_defaults(fn=get_stock_data),
        FunctionTool.from_defaults(fn=get_stock_history),
        FunctionTool.from_defaults(fn=execute_python),
        FunctionTool.from_defaults(fn=ask_user),
    ]
    
    if ctx and session_id:
        tools.append(get_finish_tool(ctx, session_id))
        
    if include_subagent:
        # We pass include_subagent=False to the subagent to avoid infinite recursion by default
        # or we could just let it be and rely on the LLM to not be stupid.
        # For now, let's allow it but be mindful.
        tools.append(FunctionTool.from_defaults(async_fn=call_subagent))
        
    return tools


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
        tools = get_tools(ctx, session_id)
        
        agent = create_agent(llm, tools=tools)

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


def get_agent() -> ReActAgent:
    """Convenience function to initialize and return the fully configured agent."""
    llm = get_llm()
    tools = get_tools()
    return create_agent(llm, tools=tools)
