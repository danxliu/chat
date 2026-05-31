import logging
from typing import List

import httpx

from config import settings

logger = logging.getLogger(__name__)

AVAILABLE_MODELS: List[str] = []


async def fetch_available_models():
    global AVAILABLE_MODELS
    try:
        url = f"{settings.api_base}/models"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            models = [f"openai/{m['id']}" for m in data.get("data", [])]

            AVAILABLE_MODELS.clear()
            if not models:
                logger.warning(f"No models found at {url}")
            AVAILABLE_MODELS.extend(models)
            logger.info(
                f"Successfully fetched {len(models)} models from {url}: {AVAILABLE_MODELS}"
            )
    except Exception as e:
        logger.error(f"Failed to fetch models from {settings.api_base}: {e}")
        AVAILABLE_MODELS.clear()
