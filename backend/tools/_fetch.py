import io
import logging
from dataclasses import dataclass

import httpx
import trafilatura
from pypdf import PdfReader

logger = logging.getLogger(__name__)

MAX_BYTES = 30 * 1024 * 1024  # 30 MB
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
TIMEOUT_S = 30.0
MAX_PDF_PAGES = 50

IMAGE_MIME_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    }
)

USER_AGENT = "Mozilla/5.0 (compatible; ChatBot/1.0; +https://github.com/daniel/chat)"
ACCEPT_HEADER = "text/html,application/pdf,image/png,image/jpeg,image/webp,image/gif"


@dataclass
class FetchResult:
    ok: bool
    data: bytes | None = None
    content_type: str | None = None
    final_url: str | None = None
    error: str | None = None


async def fetch_url(
    url: str,
    max_bytes: int = MAX_BYTES,
    timeout_s: float = TIMEOUT_S,
) -> FetchResult:
    """Downloads a URL and returns raw bytes with metadata.

    Args:
        url: The URL to fetch (http/https only).
        max_bytes: Maximum bytes to download before aborting.
        timeout_s: Total timeout in seconds (connect, read, write).

    Returns:
        FetchResult with ok=True and payload on success, or ok=False and error.
    """
    if not url.startswith(("http://", "https://")):
        return FetchResult(
            ok=False, error="Only http:// and https:// URLs are allowed."
        )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": ACCEPT_HEADER,
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout_s),
            headers=headers,
        ) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                content_type = response.headers.get(
                    "content-type", "application/octet-stream"
                )
                ct_main = content_type.split(";")[0].strip()

                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        return FetchResult(
                            ok=False,
                            error=f"Response exceeds {max_bytes / 1024 / 1024:.0f} MB limit.",
                        )

                return FetchResult(
                    ok=True,
                    data=bytes(body),
                    content_type=ct_main,
                    final_url=str(response.url),
                )

    except httpx.TimeoutException:
        return FetchResult(ok=False, error=f"Request timed out after {timeout_s:.0f}s.")
    except httpx.HTTPStatusError as e:
        return FetchResult(
            ok=False,
            error=f"HTTP {e.response.status_code} for {url}",
        )
    except httpx.HTTPError as e:
        return FetchResult(ok=False, error=f"Request failed: {e}")
    except Exception as e:
        logger.exception("Unexpected error fetching %s", url)
        return FetchResult(ok=False, error=f"Unexpected error: {e}")


def extract_pdf_text(data: bytes, max_pages: int = MAX_PDF_PAGES) -> str:
    """Extract plain text from raw PDF bytes.

    Args:
        data: Raw PDF file bytes.
        max_pages: Maximum number of pages to process.

    Returns:
        Extracted text with pages separated by newlines.

    Raises:
        Various pypdf errors on corrupt or encrypted PDFs.
    """
    reader = PdfReader(io.BytesIO(data))
    pages = reader.pages[: min(len(reader.pages), max_pages)]
    return "".join((page.extract_text() or "") + "\n" for page in pages)


def extract_html_text(data: bytes) -> str | None:
    """Extract the main text content from HTML bytes using trafilatura.

    Args:
        data: Raw HTML bytes.

    Returns:
        Markdown string with links preserved, or None if extraction produced nothing.
    """
    return trafilatura.extract(data, include_links=True, output_format="markdown")
