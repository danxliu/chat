from typing import List, Optional
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic model to manage configuration from .env"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_base: str = "http://localhost:13305/v1"
    api_key: str = "dummy-key"
    model_str: str = Field(default="local-model", alias="model")
    title_model: str = "local-model"
    max_tokens: int = 8192
    temperature: float = 0.1
    timeout: float = 600.0
    step_threshold: int = 15
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379

    @computed_field
    @property
    def models(self) -> List[str]:
        return [m.strip() for m in self.model_str.split(",") if m.strip()]


settings = Settings()
