import inspect
from typing import Any, Callable, Dict, List, Type

from pydantic import create_model
from pydantic.main import BaseModel

from config import settings
from tools.execute_python import execute_python
from tools.finance import get_stock_data, get_stock_history
from tools.web_scrape import web_scrape
from tools.web_search import web_search
from tools.draw_chart import draw_chart
from tools.suggest_continuations import suggest_continuations


def get_tools() -> List[Callable]:
    """Returns the list of tool functions available to the agent."""
    return [
        web_search,
        web_scrape,
        get_stock_data,
        get_stock_history,
        execute_python,
        draw_chart,
        suggest_continuations,
    ]


def _get_tool_models() -> Dict[str, Type[BaseModel]]:
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


def get_tools_schema() -> List[Dict[str, Any]]:
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


def execute_tool(name: str, kwargs: Dict[str, Any]) -> str:
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
        return str(tool_map[name](**kwargs))
    except Exception as e:
        return f"Error executing tool '{name}': {e}"


def get_completion_args(model: str, api_base: str | None = None) -> Dict[str, Any]:
    """Returns the default arguments for LiteLLM completion."""
    return {
        "model": model,
        "api_base": api_base or settings.llm_api_base,
        "api_key": settings.api_key,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "frequency_penalty": settings.frequency_penalty,
        "presence_penalty": settings.presence_penalty,
        "timeout": settings.timeout,
    }
