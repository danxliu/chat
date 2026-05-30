import trafilatura
from llama_index.core.tools import FunctionTool
from tools.subagent import call_subagent

def scrape_url(url: str) -> str:
    """Raw tool to extract content from a URL. Only for subagent use."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return f"Failed to fetch content from {url}. Please check the URL and your internet connection."
        
        result = trafilatura.extract(downloaded, include_links=True, output_format="markdown")
        if not result:
            return f"Failed to extract content from {url}. The page might be empty or blocking scrapers."
        
        # Truncate content to avoid context overflow (approx 15,000 characters)
        return result[:15000]
    except Exception as e:
        return f"Error during scraping {url}: {e}"

async def web_scrape(url: str) -> str:
    """Uses a specialized subagent to scrape and summarize the content of a given URL."""
    scrape_tool = FunctionTool.from_defaults(fn=scrape_url)
    
    query = (
        f"Please scrape the following URL and provide a comprehensive yet concise summary of its main content: {url}. "
        "Use the scrape_url tool provided to get the content first."
    )
    
    try:
        summary = await call_subagent(query, tools=[scrape_tool])
        return f"Summary of {url}:\n\n{summary}"
    except Exception as e:
        return f"Failed to delegate web scraping for {url}. Error: {e}"
