from typing import List
from llama_index.core.agent import AgentRunner, FunctionCallingAgentWorker
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai_like import OpenAILike
from config import settings

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
