import base64
import json
import logging
from typing import Any

import litellm
import numpy as np
from fastembed import TextEmbedding
from pydantic import BaseModel, Field

from agent import get_completion_args
from config import settings
from storage import chat_storage

logger = logging.getLogger(__name__)


class ExtractedFacts(BaseModel):
    facts: list[str] = Field(default_factory=list)


FACT_EXTRACTION_PROMPT = """You are a memory extraction system. Analyze the following conversation exchange between a user and an AI assistant.

Extract discrete, standalone facts and preferences about the user that would be useful to remember for future conversations. Focus on:
- Personal details and preferences (name, location, job, likes/dislikes)
- Projects or tasks the user is working on
- Technical preferences (languages, frameworks, tools)
- Decisions or opinions the user expresses
- Any other lasting information

Return ONLY a JSON array of strings, each representing one fact. Each fact should be a complete sentence that stands alone without context from the conversation.
Example output: ["User works as a software engineer at Acme Corp.", "User prefers Python over JavaScript.", "User is building a stock analysis dashboard."]

If no meaningful facts are found, return an empty JSON array: []

User message: {user_msg}

Assistant response: {assistant_msg}

JSON array of facts:"""


class MemoryManager:
    DEFAULT_USER_ID = "default"

    def __init__(self, user_id: str | None = None):
        self.user_id = user_id or self.DEFAULT_USER_ID
        self._embedder: TextEmbedding | None = None

    @property
    def embedder(self) -> TextEmbedding:
        if self._embedder is None:
            logger.info("Loading embedding model %s...", settings.embedding_model)
            self._embedder = TextEmbedding(
                model_name=settings.embedding_model, threads=2
            )
            logger.info("Embedding model loaded.")
        return self._embedder

    def _encode_embedding(self, embedding: np.ndarray) -> str:
        return base64.b64encode(embedding.astype(np.float32).tobytes()).decode()

    def _decode_embedding(self, b64_str: str) -> np.ndarray:
        return np.frombuffer(base64.b64decode(b64_str), dtype=np.float32)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    async def retrieve(self, query: str, top_k: int | None = None) -> str:
        top_k = top_k or settings.memory_top_k

        memories = await chat_storage.get_memories(self.user_id)
        if not memories:
            return ""

        query_embedding = next(iter(self.embedder.query_embed([query])))

        scored: list[tuple[float, dict[str, Any]]] = []
        for mem in memories:
            mem_emb = self._decode_embedding(mem["embedding"])
            score = self._cosine_similarity(query_embedding, mem_emb)
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_memories = [mem for _, mem in scored[:top_k] if _ > 0.1]

        if not top_memories:
            return ""

        lines = ["The following are relevant facts remembered about the user:"]
        for i, mem in enumerate(top_memories, 1):
            lines.append(f"{i}. {mem['content']}")
        return "\n".join(lines)

    async def extract_and_store(self, user_msg: str, assistant_msg: str) -> None:
        facts = await self._extract_facts(user_msg, assistant_msg)
        if not facts:
            return

        embeddings = list(
            self.embedder.passage_embed(facts, batch_size=min(len(facts), 32))
        )

        for fact, emb in zip(facts, embeddings):
            emb_b64 = self._encode_embedding(emb)
            await chat_storage.add_memory(self.user_id, fact, emb_b64)

        logger.info("Stored %d new memories for user '%s'", len(facts), self.user_id)

    async def count(self) -> int:
        memories = await chat_storage.get_memories(self.user_id)
        return len(memories)

    async def clear(self) -> None:
        await chat_storage.delete_memories(self.user_id)

    async def _extract_facts(self, user_msg: str, assistant_msg: str) -> list[str]:
        prompt = FACT_EXTRACTION_PROMPT.format(
            user_msg=user_msg[:2000],
            assistant_msg=assistant_msg[:4000],
        )

        completion_args = get_completion_args(model=settings.memory_extraction_model)
        # Remove streaming-related keys — this is a non-streaming call
        completion_args.pop("stream_options", None)
        completion_args.pop("tools", None)
        completion_args.pop("tool_choice", None)
        completion_args.pop("extra_body", None)
        completion_args["temperature"] = 0.0  # deterministic extraction

        try:
            response = await litellm.acompletion(
                **completion_args,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content
            if not raw:
                return []

            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:]) if len(lines) > 1 else raw
                if raw.endswith("```"):
                    raw = raw[:-3].strip()

            data = json.loads(raw)
            if isinstance(data, list):
                data = {"facts": data}

            validated = ExtractedFacts.model_validate(data)
            return [f.strip() for f in validated.facts if f.strip()]

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse/validate fact extraction response: %s", e)
            return []
        except Exception:
            logger.exception("Fact extraction failed")
            return []
