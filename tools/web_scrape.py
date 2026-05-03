import trafilatura
from tools.subagent import call_subagent
from prompts.web_summarizer import WEB_SUMMARIZER_PROMPT
from prompts import RichPromptTemplate

async def web_scrape(url: str) -> str:
    """Uses trafilatura to scrape the content of a given URL and summarizes it using a subagent."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return f"Failed to fetch content from {url}. Please check the URL and your internet connection."
        
        result = trafilatura.extract(downloaded, include_links=True, output_format="markdown")
        if not result:
            return f"Failed to extract content from {url}. The page might be empty or blocking scrapers."
        
        # Truncate content to avoid context overflow (approx 15,000 characters)
        truncated_content = result[:15000]
        if len(result) > 15000:
            truncated_content += "\n\n[... content truncated ...]"

        # Use a subagent to summarize the content
        try:
            prompt_template = RichPromptTemplate(WEB_SUMMARIZER_PROMPT)
            summary_query = prompt_template.format(content=truncated_content)
            
            summary = await call_subagent(summary_query, tools=None)
            return f"Summary of {url}:\n\n{summary}"
        except Exception as sub_e:
            return f"Scraping successful, but summarization failed. This usually indicates an issue with the LLM connection (call_subagent). Error: {sub_e}\n\nRaw content (first 500 chars):\n{truncated_content[:500]}"
        
    except Exception as e:
        return f"Unexpected error during web scraping: {e}"
