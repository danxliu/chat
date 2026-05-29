from typing import List, Optional

from llama_index.core.agent import ReActAgent
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
) -> ReActAgent:
    return ReActAgent.from_tools(
        tools, llm=llm, chat_history=chat_history or [], verbose=True
    )
