from llama_index.core.agent import AgentRunner, FunctionCallingAgentWorker
from llama_index.llms.openai_like import OpenAILike

from config import settings


def setup_local_llm() -> OpenAILike:
    """Configures the LLM to connect to the local OpenAI-compatible endpoint."""
    return OpenAILike(
        api_base=settings.api_base,
        api_key=settings.api_key,
        model=settings.model,
        is_function_calling_model=True,
        is_chat_model=True,
        temperature=settings.temperatrure,
        max_tokens=settings.max_tokens,
    )


def create_agent(llm: OpenAILike) -> AgentRunner:
    """Creates the agent worker and wraps it in a runner loop."""
    agent_worker = FunctionCallingAgentWorker.from_tools([], llm=llm, verbose=True)
    return AgentRunner(agent_worker)


def get_agent() -> AgentRunner:
    """Convenience function to initialize and return the fully configured agent."""
    llm = setup_local_llm()
    return create_agent(llm)
