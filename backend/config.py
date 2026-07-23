from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
    )

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    FRONTEND_BUILD_DIR: Path = BASE_DIR / "frontend" / "build"

    # LLM API
    llm_api_base: str = ""
    api_key: str = ""
    model: str = "deepseek-v4-pro"

    # Completion defaults
    max_tokens: int = 32768
    temperature: float = 0.6
    frequency_penalty: float = 0.5
    presence_penalty: float = 0.2
    timeout: float = 600.0
    step_threshold: int = 15

    # Sentiment tool
    sentiment_model: str = "deepseek-v4-flash"
    sentiment_max_articles: int = 10
    sentiment_max_concurrency: int = 3

    # HuggingFace
    hf_token: str = ""

    # Memory (cross-session persistent memory)
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_cache_dir: str = ""
    memory_top_k: int = 5
    memory_max_count: int = 1000
    memory_extraction_model: str = "deepseek-v4-flash"

    # Context window management (auto-compaction)
    max_context_tokens: int = 100000
    compaction_trigger_pct: float = 0.75
    compaction_keep_recent: int = 6
    compaction_model: str = "deepseek-v4-flash"
    compaction_max_tokens: int = 2048
    compaction_temperature: float = 0.0
    compaction_tool_result_max_chars: int = 500

    # OpenRouteService (geolocation tools)
    ors_api_key: str = ""

    # Redis
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379


settings = Settings()
