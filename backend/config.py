import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic model to manage configuration from .env"""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
    )

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    FRONTEND_BUILD_DIR: Path = BASE_DIR / "frontend" / "build"

    # OpenCode Go API
    opencode_api_base: str = ""
    opencode_api_key: str = ""

    default_model: str = ""

    # Completion defaults
    max_tokens: int = 32768
    temperature: float = 0.6
    frequency_penalty: float = 0.5
    presence_penalty: float = 0.2
    timeout: float = 600.0
    step_threshold: int = 15

    # Redis
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379


settings = Settings()
