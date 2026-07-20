from typing import Any

from openai import AsyncOpenAI

from config import settings

openai_client = AsyncOpenAI(
    base_url=settings.llm_api_base,
    api_key=settings.api_key,
    timeout=settings.timeout,
)


def get_completion_args(model: str) -> dict[str, Any]:
    """Returns the default per-request arguments for chat completions."""
    return {
        "model": model,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "frequency_penalty": settings.frequency_penalty,
        "presence_penalty": settings.presence_penalty,
    }
