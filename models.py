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
            chat_models = [
                f"openai/{m['id']}" for m in data.get("data", []) if "chat" in m["id"]
            ]
            AVAILABLE_MODELS.clear()
            AVAILABLE_MODELS.extend(chat_models)

            if not AVAILABLE_MODELS:
                logger.warning(f"No chat models found at {url}")
            logger.info(
                f"Successfully fetched {len(AVAILABLE_MODELS)} chat models from {url}: {AVAILABLE_MODELS}"
            )
    except Exception as e:
        logger.error(f"Failed to fetch models from {settings.api_base}: {e}")
        AVAILABLE_MODELS.clear()
