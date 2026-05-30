from typing import List, Callable

from tools.execute_python import execute_python
from tools.finance import get_stock_data, get_stock_history
from tools.finish import finish
from tools.web_scrape import web_scrape
from tools.web_search import web_search


def get_tools(include_finish: bool = True) -> List[Callable]:
    """Returns the list of tool functions available to the agent."""
    tools = [
        web_search,
        web_scrape,
        get_stock_data,
        get_stock_history,
        execute_python,
    ]

    if include_finish:
        tools.append(finish)

    return tools
