from typing import Any, Callable, Dict, List

from config import settings
from tools.execute_python import execute_python
from tools.finance import get_stock_data, get_stock_history
from tools.web_scrape import web_scrape
from tools.web_search import web_search


def get_tools() -> List[Callable]:
    """Returns the list of tool functions available to the agent."""
    return [
        web_search,
        web_scrape,
        get_stock_data,
        get_stock_history,
        execute_python,
    ]


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
