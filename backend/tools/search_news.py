from ddgs import DDGS


def search_news(query: str, max_results: int = 5) -> str:
    """
    Searches for recent news articles matching the query.

    Use this when the user asks for current events, breaking news,
    or recent developments on a topic.

    Args:
        query (str): The search query for news.
        max_results (int): Max results (1-20, default 5).
    """
    try:
        max_results = max(1, min(max_results, 20))
        results = list(DDGS().news(query, max_results=max_results))
        if not results:
            return "No news results found."

        md = ["### News Search Results:"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No Title")
            url = r.get("url", "")
            body = r.get("body", "")
            source = r.get("source", "Unknown")
            date = r.get("date", "")

            md.append(f"{i}. **[{title}]({url})**\n   _{source}_ — {date}\n\n   {body}")

        return "\n\n".join(md)
    except Exception as e:
        return f"Error during news search: {e}"
