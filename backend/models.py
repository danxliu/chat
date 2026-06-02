import logging
from typing import List, Optional
from pydantic import BaseModel
from config import settings

logger = logging.getLogger(__name__)

AVAILABLE_MODELS: List[str] = [settings.model]


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
    content: str
    thought: Optional[str] = None
    attachments: Optional[List[Attachment]] = None
    metrics: Optional[Metrics] = None


class HistoryResponse(BaseModel):
    history: List[ChatMessage]
