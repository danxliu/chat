from typing import Any, Optional
from agent_factory import get_llm, create_agent

async def call_subagent(query: str, tools: Optional[Any] = None) -> str:
    """
    Spawns a subagent to handle a specific query.
    If tools are provided, the subagent will have access to them.
    Otherwise, it will be a bare agent (useful for simple tasks like summarization).
    """
    llm = get_llm()
    agent = create_agent(llm, tools or [])
    response = await agent.achat(query)
    return str(response)
