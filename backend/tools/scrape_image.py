import logging
import ssl

import easyocr

from tools._fetch import IMAGE_MIME_TYPES, MAX_IMAGE_BYTES, fetch_url

logger = logging.getLogger(__name__)

MAX_CHARS = 8000

_reader: easyocr.Reader | None = None


def _get_reader() -> easyocr.Reader:
    """Lazy-init the EasyOCR reader so models are only loaded on first use."""
    global _reader
    if _reader is not None:
        return _reader

    logger.info("Initializing EasyOCR reader (first use)...")
    try:
        _reader = easyocr.Reader(["en"], gpu=True)
    except Exception:
        # Some environments lack CA certificates for model downloads.

        ssl._create_default_https_context = ssl._create_unverified_context  # noqa: S323
        logger.warning("SSL verification disabled for EasyOCR model download.")
        _reader = easyocr.Reader(["en"], gpu=True)

    logger.info("EasyOCR reader ready.")
    return _reader


async def scrape_image(url: str) -> str:
    """
    Downloads an image from a URL and extracts any visible text using OCR.

    Args:
            url (str): The URL of the image to scrape (png, jpeg, webp, gif).
    """
    try:
        result = await fetch_url(url, max_bytes=MAX_IMAGE_BYTES)
        if not result.ok:
            return f"Failed to fetch image from {url}: {result.error}"
        if result.data is None:
            return f"Failed to fetch image from {url}: empty response body."

        ct = result.content_type
        if ct not in IMAGE_MIME_TYPES:
            return (
                f"URL does not point to a supported image: got {ct}. "
                f"Supported types: {', '.join(sorted(IMAGE_MIME_TYPES))}."
            )

        reader = _get_reader()
        # detail=0 returns list[str] at runtime; type stubs don't narrow on the param.
        raw = reader.readtext(result.data, detail=0)
        if not raw:
            return f"No text found in image at {url}."

        body = "\n".join(str(item) for item in raw)
        return (
            f"### OCR from image: {url}\n"
            f"Content-Type: {ct}, size: {len(result.data)} bytes\n\n"
            f"{body[:MAX_CHARS]}"
        )
    except Exception as e:
        return f"Error during image scraping {url}: {e}"
