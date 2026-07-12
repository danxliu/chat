import json
import time
from typing import Any

import redis.asyncio as redis

from config import settings


class ChatStorage:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host, port=settings.redis_port, decode_responses=True
        )

    def _get_key(self, session_id: str) -> str:
        return f"agent_context:{session_id}"

    async def save_context(self, session_id: str, state: dict[str, Any]) -> None:
        await self.client.set(self._get_key(session_id), json.dumps(state))
        await self.client.zadd("agent_last_updated", {session_id: time.time()})

    async def load_context(self, session_id: str) -> dict[str, Any] | None:
        data = await self.client.get(self._get_key(session_id))
        if not data:
            return None

        return json.loads(data)

    async def list_sessions(self) -> list[str]:
        # Use sorted set for ordering by most recent
        session_ids = await self.client.zrevrange("agent_last_updated", 0, -1)

        # Fallback for existing sessions that don't have a timestamp yet
        if not session_ids:
            keys = await self.client.keys("agent_context:*")
            session_ids = [key.split(":")[-1] for key in keys]

        return session_ids

    async def save_title(self, session_id: str, title: str) -> None:
        await self.client.hset("agent_titles", session_id, title)
        await self.client.zadd("agent_last_updated", {session_id: time.time()})

    async def get_title(self, session_id: str) -> str | None:
        return await self.client.hget("agent_titles", session_id)

    async def list_sessions_with_titles(self) -> list[dict[str, str]]:
        session_ids = await self.list_sessions()
        titles = await self.client.hgetall("agent_titles")
        return [
            {"session_id": sid, "title": titles.get(sid, "New Chat")}
            for sid in session_ids
        ]

    async def delete_context(self, session_id: str) -> None:
        await self.client.delete(self._get_key(session_id))
        await self.client.hdel("agent_titles", session_id)
        await self.client.zrem("agent_last_updated", session_id)

    async def clear_all(self) -> None:
        keys = await self.client.keys("agent_context:*")
        if keys:
            await self.client.delete(*keys)
        await self.client.delete("agent_titles")
        await self.client.delete("agent_last_updated")


chat_storage = ChatStorage()
