from typing import List, Optional

from llama_index.core.agent import AgentRunner, FunctionCallingAgentWorker
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai_like import OpenAILike

from config import settings


def get_llm() -> OpenAILike:
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


def create_agent(
    llm: OpenAILike,
    tools: List[FunctionTool],
    chat_history: Optional[List[ChatMessage]] = None,
) -> AgentRunner:
    worker = FunctionCallingAgentWorker.from_tools(
        tools, llm=llm, verbose=True
    )
    return AgentRunner(worker, chat_history=chat_history or [])
