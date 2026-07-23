import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger(__name__)

AVAILABLE_MODELS: list[str] = []


def get_model_context_limit(model_name: str | None = None) -> int:
    """Return the max context token limit for a model."""
    return settings.max_context_tokens


async def refresh_models() -> list[str]:
    """Fetch available models from OpenCode Go. Falls back to hardcoded default."""
    global AVAILABLE_MODELS
    if not settings.api_key or not settings.llm_api_base:
        logger.warning(
            "OpenCode API key or base URL not set, using fallback model list"
        )
        AVAILABLE_MODELS.clear()
        AVAILABLE_MODELS.extend([settings.model])
        return AVAILABLE_MODELS

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.llm_api_base}/models",
                headers={"Authorization": f"Bearer {settings.api_key}"},
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

    fallback = [settings.model]
    AVAILABLE_MODELS.clear()
    AVAILABLE_MODELS.extend([settings.model])
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
    blocks: list[Block] = Field(default_factory=list)
    thought: str | None = None
    attachments: list[Attachment] | None = None
    metrics: Metrics | None = None


class HistoryResponse(BaseModel):
    history: list[ChatMessage]
    token_usage: dict | None = None
