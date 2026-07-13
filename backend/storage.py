import json
import time
import uuid
from typing import Any

import redis.asyncio as redis

from config import settings


class ChatStorage:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host, port=settings.redis_port, decode_responses=True
        )

    def _context_key(self, user_id: str, session_id: str) -> str:
        return f"agent_context:{user_id}:{session_id}"

    def _updated_key(self, user_id: str) -> str:
        return f"agent_last_updated:{user_id}"

    def _titles_key(self, user_id: str) -> str:
        return f"agent_titles:{user_id}"

    async def save_context(
        self, user_id: str, session_id: str, state: dict[str, Any]
    ) -> None:
        await self.client.set(self._context_key(user_id, session_id), json.dumps(state))
        await self.client.zadd(self._updated_key(user_id), {session_id: time.time()})

    async def load_context(
        self, user_id: str, session_id: str
    ) -> dict[str, Any] | None:
        data = await self.client.get(self._context_key(user_id, session_id))
        if not data:
            return None
        return json.loads(data)

    async def list_sessions(self, user_id: str) -> list[str]:
        session_ids = await self.client.zrevrange(self._updated_key(user_id), 0, -1)

        # Fallback for sessions that don't have a timestamp yet
        if not session_ids:
            keys = await self.client.keys(f"agent_context:{user_id}:*")
            session_ids = [key.split(":", 2)[-1] for key in keys]

        return session_ids

    async def save_title(self, user_id: str, session_id: str, title: str) -> None:
        await self.client.hset(self._titles_key(user_id), session_id, title)
        await self.client.zadd(self._updated_key(user_id), {session_id: time.time()})

    async def get_title(self, user_id: str, session_id: str) -> str | None:
        return await self.client.hget(self._titles_key(user_id), session_id)

    async def list_sessions_with_titles(self, user_id: str) -> list[dict[str, str]]:
        session_ids = await self.list_sessions(user_id)
        titles = await self.client.hgetall(self._titles_key(user_id))
        return [
            {"session_id": sid, "title": titles.get(sid, "New Chat")}
            for sid in session_ids
        ]

    async def delete_context(self, user_id: str, session_id: str) -> None:
        await self.client.delete(self._context_key(user_id, session_id))
        await self.client.hdel(self._titles_key(user_id), session_id)
        await self.client.zrem(self._updated_key(user_id), session_id)

    async def add_memory(self, user_id: str, content: str, embedding_b64: str) -> str:
        """Add a memory with its embedding for a user."""
        memory_id = str(uuid.uuid4())
        memory = json.dumps(
            {
                "id": memory_id,
                "content": content,
                "embedding": embedding_b64,
                "created_at": time.time(),
            }
        )
        key = f"user_memories:{user_id}"
        await self.client.lpush(key, memory)
        await self.client.ltrim(key, 0, settings.memory_max_count - 1)
        return memory_id

    async def get_memories(self, user_id: str) -> list[dict[str, Any]]:
        """Retrieve all memories for a user (ordered newest first)."""
        key = f"user_memories:{user_id}"
        data = await self.client.lrange(key, 0, -1)
        return [json.loads(d) for d in data]

    async def delete_memories(self, user_id: str) -> None:
        """Delete all memories for a user."""
        key = f"user_memories:{user_id}"
        await self.client.delete(key)

    async def clear_all(self, user_id: str) -> None:
        context_keys = await self.client.keys(f"agent_context:{user_id}:*")
        if context_keys:
            await self.client.delete(*context_keys)
        await self.client.delete(self._titles_key(user_id))
        await self.client.delete(self._updated_key(user_id))


chat_storage = ChatStorage()
