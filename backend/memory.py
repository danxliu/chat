import logging
from typing import Optional
from mem0 import Memory
from config import settings

logger = logging.getLogger(__name__)


def _clean_model_name(model: str) -> str:
    return model.split("/", 1)[-1]


def _get_memory_config(
    embedding_model: Optional[str] = None, embed_api_base: Optional[str] = None
) -> dict:
    return {
        "llm": {
            "provider": "openai",
            "config": {
                "model": _clean_model_name(settings.model),
                "api_key": settings.api_key,
                "openai_base_url": settings.llm_api_base,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": _clean_model_name(embedding_model or settings.embedding_model),
                "api_key": settings.api_key,
                "openai_base_url": embed_api_base or settings.embed_api_base,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "memories",
                "path": settings.mem0_dir,
            },
        },
        "history_db_path": f"{settings.mem0_dir}/history.db",
    }


# Global cache for memory instance
_memory_instance: Optional[Memory] = None
_last_config: Optional[dict] = None


def get_memory(
    embedding_model: Optional[str] = None, embed_api_base: Optional[str] = None
) -> Memory:
    global _memory_instance, _last_config
    config = _get_memory_config(embedding_model, embed_api_base)

    if _memory_instance is None or config != _last_config:
        logger.info("Initializing/Re-initializing memory with new config")
        _memory_instance = Memory.from_config(config)
        _last_config = config

    return _memory_instance


def add_memory(
    content: str,
    user_id: str = "default_user",
    metadata: dict = None,
    embedding_model: Optional[str] = None,
    embed_api_base: Optional[str] = None,
):
    try:
        mem = get_memory(embedding_model, embed_api_base)
        mem.add(content, user_id=user_id, metadata=metadata)
        logger.info(f"Added memory for user {user_id}")
    except Exception:
        logger.exception(f"Failed to add memory for user {user_id}")


def search_memories(
    query: str,
    user_id: str = "default_user",
    limit: int = 5,
    embedding_model: Optional[str] = None,
    embed_api_base: Optional[str] = None,
):
    try:
        mem = get_memory(embedding_model, embed_api_base)
        filters = {"user_id": user_id}
        response = mem.search(query, filters=filters, limit=limit)
        results = response.get("results", [])
        return [res["memory"] for res in results]
    except Exception:
        logger.exception(f"Failed to search memories for user {user_id}")
        return []


def reset_memory():
    try:
        mem = get_memory()
        mem.reset()
        logger.info("Memory reset successful")
    except Exception:
        logger.exception("Failed to reset memory")
