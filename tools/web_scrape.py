import trafilatura

def web_scrape(url: str) -> str:
    """Uses trafilatura to scrape the content of a given URL."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return f"Failed to fetch content from {url}."
        
        result = trafilatura.extract(downloaded, include_links=True, output_format="markdown")
        if not result:
            return f"Failed to extract content from {url}."
        return result
    except Exception as e:
        return f"Error during web scraping: {e}"