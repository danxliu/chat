import logging
from typing import Any, List, Optional

import httpx
from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger(__name__)

AVAILABLE_MODELS: List[str] = []


async def refresh_models() -> List[str]:
    """Fetch available models from OpenCode Go. Falls back to hardcoded default."""
    global AVAILABLE_MODELS
    if not settings.opencode_api_key or not settings.opencode_api_base:
        logger.warning(
            "OpenCode API key or base URL not set, using fallback model list"
        )
        AVAILABLE_MODELS.clear()
        AVAILABLE_MODELS.extend([settings.default_model])
        return AVAILABLE_MODELS

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.opencode_api_base}/models",
                headers={"Authorization": f"Bearer {settings.opencode_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            models = [m["id"] for m in data.get("data", []) if m.get("id")]
            if models:
                AVAILABLE_MODELS.clear()
                AVAILABLE_MODELS.extend(models)
                logger.info(f"Loaded {len(models)} models from OpenCode Go")
                return models
    except Exception:
        logger.exception("Failed to fetch models from OpenCode Go, using fallback")

    fallback = [settings.default_model]
    AVAILABLE_MODELS.clear()
    AVAILABLE_MODELS.extend([settings.default_model])
    return fallback


class Block(BaseModel):
    index: int
    type: str  # e.g., "text", "chart"
    content: Any


class Attachment(BaseModel):
    file_id: str
    filename: str
    stored_filename: str
    mime_type: str


class Metrics(BaseModel):
    tokens: int
    time_s: float
    tokens_per_sec: float


class ChatMessage(BaseModel):
    role: str
    blocks: List[Block] = Field(default_factory=list)
    thought: Optional[str] = None
    attachments: Optional[List[Attachment]] = None
    metrics: Optional[Metrics] = None


class HistoryResponse(BaseModel):
    history: List[ChatMessage]
