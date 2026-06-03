from typing import List, Dict, Any

def draw_chart(chart_type: str, title: str, data: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    """
    Draw a graph (bar, line, pie, area) with the given data and configuration.
    
    Args:
        chart_type: The type of chart (bar, line, pie, area).
        title: The title of the chart.
        data: The array of objects describing the data points.
        config: The configuration mapping data keys to axes (e.g., {"xAxisKey": "month", "yAxisKeys": ["organic", "paid"]}).
    """
    # The tool doesn't do anything on the backend side, it just returns a success message.
    # The frontend will intercept the tool call history to render the chart.
    return f"Successfully generated a {chart_type} chart titled '{title}'."
