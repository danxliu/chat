from typing import List

from llama_index.core.agent import AgentRunner
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from agent_factory import create_agent, get_llm
from tools.execute_python import execute_python
from tools.finance import get_stock_data, get_stock_history
from tools.finish import get_finish_tool
from tools.subagent import call_subagent
from tools.web_scrape import web_scrape
from tools.web_search import web_search


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
def get_agent() -> AgentRunner:
    llm = get_llm()
    tools = get_tools()
    return create_agent(llm, tools=tools)
