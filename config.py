from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic model to manage configuration from .env"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_base: str = "http://localhost:13305/v1"
    api_key: str = "dummy-key"
    model: str = "local-model"
    max_tokens: int = 8192
    temperature: float = 0.1
    timeout: float = 600.0
    step_threshold: int = 15


settings = Settings()
