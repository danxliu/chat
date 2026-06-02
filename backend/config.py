from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic model to manage configuration from .env"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_api_base: str = "http://localhost:13305/v1"
    embed_api_base: str = "http://localhost:8081/v1"
    api_key: str = "dummy-key"
    model: str = "openai/chat-local"
    max_tokens: int = 8192
    temperature: float = 0.6
    frequency_penalty: float = 0.5
    presence_penalty: float = 0.2
    timeout: float = 600.0
    step_threshold: int = 15
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    mem0_dir: str = ".mem0"
    embedding_model: str = "openai/embed-local"


settings = Settings()
