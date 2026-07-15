from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    """
    Searches the web for the given query using DuckDuckGo.

    Use this for general web searches to find up-to-date information,
    documentation, or any content not in your training data.

    Args:
        query (str): The search query.
        max_results (int): Max results (1-20, default 5).
    """
    try:
        max_results = max(1, min(max_results, 20))
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return "No results found."

        md_results = ["### Web Search Results:"]
        for res in results:
            title = res.get("title", "No Title")
            link = res.get("href", res.get("link", ""))
            body = res.get("body", "")
            md_results.append(f"- **[{title}]({link})**\n  {body}")

        return "\n\n".join(md_results)
    except Exception as e:
        return f"Error during web search: {e}"
