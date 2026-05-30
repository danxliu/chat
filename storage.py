import json
from typing import Optional

import redis.asyncio as redis
from llama_index.core.workflow import Context, Workflow
from llama_index.core.workflow.context_serializers import JsonSerializer

from config import settings


class ChatStorage:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host, port=settings.redis_port, decode_responses=True
        )
        self.serializer = JsonSerializer()

    def _get_key(self, session_id: str) -> str:
        return f"agent_context:{session_id}"

    async def save_context(self, session_id: str, ctx: Context) -> None:
        ctx_dict = ctx.to_dict(serializer=self.serializer)
        await self.client.set(self._get_key(session_id), json.dumps(ctx_dict))

    async def load_context(
        self, session_id: str, workflow: Workflow
    ) -> Optional[Context]:
        data = await self.client.get(self._get_key(session_id))
        if not data:
            return None

        ctx_dict = json.loads(data)
        return Context.from_dict(workflow, ctx_dict, serializer=self.serializer)

    async def list_sessions(self) -> list[str]:
        keys = await self.client.keys("agent_context:*")
        return [key.split(":")[-1] for key in keys]

    async def delete_context(self, session_id: str) -> None:
        """Deletes the session context from Redis."""
        await self.client.delete(self._get_key(session_id))


chat_storage = ChatStorage()
