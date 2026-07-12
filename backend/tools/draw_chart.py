from typing import Any

def draw_chart(chart_type: str, title: str, data: list[dict[str, Any]], label_key: str, value_keys: list[str]) -> str:
    """
    Draw a graph (bar, line, pie, area) with the given data.
    
    Args:
        chart_type: The type of chart (bar, line, pie, area).
        title: The title of the chart.
        data: The array of objects describing the data points.
        label_key: The key in the data objects to use for the X-axis or category labels (e.g., 'Date', 'month', 'browser').
        value_keys: The list of keys in the data objects to use for the Y-axis or values (e.g., ['Close'], ['usage'], ['organic', 'paid']).
    """
    # The tool doesn't do anything on the backend side, it just returns a success message.
    # The frontend will intercept the tool call history to render the chart.
    return f"Successfully generated a {chart_type} chart titled '{title}'."
