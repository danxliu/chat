import logging
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from config import settings

logger = logging.getLogger(__name__)

AVAILABLE_MODELS: List[str] = [settings.model]


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
