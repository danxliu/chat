import asyncio
import inspect
from typing import Any, Callable, Type

from pydantic import create_model
from pydantic.main import BaseModel

from config import settings
from tools.draw_chart import draw_chart
from tools.execute_python import execute_python
from tools.finance import get_stock_data, get_stock_history
from tools.fundamental_analysis import run_fundamental_analysis
from tools.geolocation import (
    distance_matrix,
    get_directions,
    reverse_geocode,
    search_location,
    search_nearby,
)
from tools.momentum_analysis import run_momentum_analysis
from tools.scrape_image import scrape_image
from tools.search_books import search_books
from tools.search_images import search_images
from tools.search_news import search_news
from tools.search_videos import search_videos
from tools.sentiment_analysis import run_sentiment_analysis
from tools.suggest_continuations import suggest_continuations
from tools.volatility_analysis import run_volatility_analysis
from tools.web_scrape import web_scrape
from tools.web_search import web_search


def get_tools() -> list[Callable]:
    """Returns the list of tool functions available to the agent."""
    return [
        web_search,
        search_images,
        search_news,
        search_videos,
        search_books,
        web_scrape,
        scrape_image,
        get_stock_data,
        get_stock_history,
        run_fundamental_analysis,
        run_momentum_analysis,
        run_volatility_analysis,
        run_sentiment_analysis,
        execute_python,
        draw_chart,
        suggest_continuations,
        search_location,
        reverse_geocode,
        get_directions,
        search_nearby,
        distance_matrix,
    ]


def _get_tool_models() -> dict[str, Type[BaseModel]]:
    """Generates Pydantic models for each tool's parameters."""
    models = {}
    for func in get_tools():
        sig = inspect.signature(func)
        fields = {}
        for name, param in sig.parameters.items():
            annotation = (
                param.annotation if param.annotation != inspect.Parameter.empty else Any
            )
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[name] = (annotation, default)

        models[func.__name__] = create_model(f"{func.__name__}Schema", **fields)
    return models


TOOL_MODELS = _get_tool_models()


def get_tools_schema() -> list[dict[str, Any]]:
    """Generates OpenAI-compatible tool schemas using Pydantic models."""
    tools = []
    tool_funcs = {func.__name__: func for func in get_tools()}

    for name, model in TOOL_MODELS.items():
        func = tool_funcs[name]
        schema = model.model_json_schema()
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": func.__doc__.split("\n")[0] if func.__doc__ else "",
                    "parameters": schema,
                },
            }
        )
    return tools


async def execute_tool(name: str, kwargs: dict[str, Any]) -> str:
    """Validates and executes a tool by name with the given arguments."""
    tool_map = {func.__name__: func for func in get_tools()}
    if name not in tool_map:
        return f"Error: Tool '{name}' not found."
    if name in TOOL_MODELS:
        try:
            validated_args = TOOL_MODELS[name](**kwargs)
            kwargs = validated_args.model_dump()
        except Exception as e:
            return f"Error: Validation failed for tool '{name}': {e}"

    try:
        func = tool_map[name]
        if inspect.iscoroutinefunction(func):
            result = await func(**kwargs)
        else:
            result = await asyncio.to_thread(func, **kwargs)
        return str(result)
    except Exception as e:
        return f"Error executing tool '{name}': {e}"


def get_completion_args(model: str) -> dict[str, Any]:
    """Returns the default arguments for LiteLLM completion."""
    return {
        "model": f"openai/{model}",
        "api_base": settings.llm_api_base,
        "api_key": settings.api_key,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "frequency_penalty": settings.frequency_penalty,
        "presence_penalty": settings.presence_penalty,
        "timeout": settings.timeout,
    }
