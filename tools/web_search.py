from ddgs import DDGS

def web_search(query: str) -> str:
    """Uses ddgs to search the web for the given query."""
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No results found."
        
        md_results = ["### Web Search Results:"]
        for res in results:
            title = res.get('title', 'No Title')
            link = res.get('href', res.get('link', ''))
            body = res.get('body', '')
            md_results.append(f"- **[{title}]({link})**\n  {body}")
        
        return "\n\n".join(md_results)
    except Exception as e:
        return f"Error during web search: {e}"