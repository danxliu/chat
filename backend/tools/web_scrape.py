from tools._fetch import extract_html_text, extract_pdf_text, fetch_url

MAX_CHARS = 15000


async def web_scrape(url: str) -> str:
    """
    Extracts the main content from a given URL and returns it in markdown format.
    Handles both HTML pages and PDF documents.

    Args:
        url (str): The URL of the website to scrape.
    """
    try:
        result = await fetch_url(url)
        if not result.ok:
            return f"Failed to fetch content from {url}: {result.error}"
        if result.data is None:
            return f"Failed to fetch content from {url}: empty response body."

        data = result.data

        match result.content_type:
            case "application/pdf":
                label, extractor = "PDF", extract_pdf_text
            case _:
                label, extractor = "HTML", extract_html_text

        try:
            text = extractor(data)
        except Exception as e:
            return f"Error extracting {label} from {url}: {e}"

        if not text:
            return (
                f"Failed to extract content from {url}."
                " The page might be empty or blocking scrapers."
            )

        body = text[:MAX_CHARS]
        if label != "HTML":
            body = f"### Extracted from {label}: {url}\n\n{body}"

        return body
    except Exception as e:
        return f"Error during scraping {url}: {e}"
