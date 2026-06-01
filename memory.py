import logging

from mem0 import Memory

from config import settings

logger = logging.getLogger(__name__)


def _clean_model_name(model: str) -> str:
    return model.split("/", 1)[-1]


config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": _clean_model_name(settings.title_model),
            "api_key": settings.api_key,
            "openai_base_url": settings.api_base,
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": _clean_model_name(settings.embedding_model),
            "api_key": settings.api_key,
            "openai_base_url": settings.api_base,
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

memory = Memory.from_config(config)


def add_memory(content: str, user_id: str = "default_user", metadata: dict = None):
    try:
        memory.add(content, user_id=user_id, metadata=metadata)
        logger.info(f"Added memory for user {user_id}")
    except Exception:
        logger.exception(f"Failed to add memory for user {user_id}")


def search_memories(query: str, user_id: str = "default_user", limit: int = 5):
    try:
        filters = {"user_id": user_id}
        response = memory.search(query, filters=filters, limit=limit)
        results = response.get("results", [])
        return [res["memory"] for res in results]
    except Exception:
        logger.exception(f"Failed to search memories for user {user_id}")
        return []
