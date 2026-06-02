import trafilatura

def web_scrape(url: str) -> str:
    """
    Extracts the main content from a given URL and returns it in markdown format.
    
    Args:
        url (str): The URL of the website to scrape.
    """
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
