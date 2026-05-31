from typing import Any, Dict

from config import settings


def get_completion_args(model: str) -> Dict[str, Any]:
    """Returns the default arguments for LiteLLM completion."""
    return {
        "model": model,
        "api_base": settings.api_base,
        "api_key": settings.api_key,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "frequency_penalty": settings.frequency_penalty,
        "presence_penalty": settings.presence_penalty,
        "timeout": settings.timeout,
    }
