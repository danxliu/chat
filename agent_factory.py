from typing import Any, Dict

from config import settings


def get_completion_args() -> Dict[str, Any]:
    """Returns the default arguments for LiteLLM completion."""
    return {
        "model": settings.model,
        "api_base": settings.api_base,
        "api_key": settings.api_key,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "timeout": settings.timeout,
    }
