import logging
from typing import List
from config import settings

logger = logging.getLogger(__name__)

AVAILABLE_MODELS: List[str] = [settings.model]
