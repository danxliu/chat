import asyncio
import logging
from enum import Enum
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError, model_validator

from models import AVAILABLE_MODELS
from storage import chat_storage
from workflow import (
    AgentExecutor,
    ContentEvent,
    ErrorEvent,
    FinalResponseEvent,
    ThoughtEvent,
    ToolCallEvent,
    WarningEvent,
)

logger = logging.getLogger(__name__)
router = APIRouter()

active_title_generations: Set[str] = set()


class MessageType(str, Enum):
    MESSAGE = "message"
    THINKING = "thinking"
    CONTENT_CHUNK = "content_chunk"
    TITLE_UPDATE = "title_update"
    PING = "ping"
    PONG = "pong"
    CANCEL = "cancel"
    ERROR = "error"
    WARNING = "warning"


class IncomingPayload(BaseModel):
    type: MessageType
    session_id: Optional[str] = None
    content: Optional[str] = None
    model: Optional[str] = None
    attachments: Optional[List[dict]] = None

    @model_validator(mode="after")
    def validate_payload(self) -> "IncomingPayload":
        if self.type == MessageType.MESSAGE:
            if not self.session_id:
                raise ValueError("Missing session_id")
            if not self.content:
                raise ValueError("Missing content")
            if not self.model:
                raise ValueError("Missing model selection")
            if not AVAILABLE_MODELS:
                raise ValueError("No models available on the server")
            if self.model not in AVAILABLE_MODELS:
                raise ValueError(f"Invalid model: {self.model}")
        return self


class ConnectionManager:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self._lock = asyncio.Lock()
        self.tasks: Set[asyncio.Task] = set()
        self.cancel_events: Dict[str, asyncio.Event] = {}

    async def send(self, payload: dict):
        async with self._lock:
            await self.ws.send_json(payload)

    async def send_error(self, message: str, session_id: str | None = None):
        await self.send(
            {
                "type": MessageType.ERROR.value,
                "session_id": session_id,
                "message": message,
            }
        )

    async def send_warning(self, message: str, session_id: str | None = None):
        await self.send(
            {
                "type": MessageType.WARNING.value,
                "session_id": session_id,
                "message": message,
            }
        )

    def spawn_task(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def get_cancel_event(self, session_id: str) -> asyncio.Event:
        if session_id not in self.cancel_events:
            self.cancel_events[session_id] = asyncio.Event()
        return self.cancel_events[session_id]

    def cleanup(self):
        for event in self.cancel_events.values():
            event.set()
        for task in self.tasks:
            task.cancel()


async def generate_title(session_id: str, query: str, conn: ConnectionManager):
    if session_id in active_title_generations:
        return
    try:
        if await chat_storage.get_title(session_id) not in (None, "New Chat"):
            return
        active_title_generations.add(session_id)
        title = await AgentExecutor(session_id).get_title(query)
        if not title:
            return
        await conn.send(
            {
                "type": MessageType.TITLE_UPDATE.value,
                "session_id": session_id,
                "title": title,
            }
        )
    except Exception:
        logger.exception(f"Failed title generation for {session_id}")
    finally:
        active_title_generations.discard(session_id)


async def process_chat(payload: IncomingPayload, conn: ConnectionManager):
    conn.spawn_task(generate_title(payload.session_id, payload.content, conn))

    cancel_event = conn.get_cancel_event(payload.session_id)
    cancel_event.clear()

    try:
        executor = AgentExecutor(payload.session_id)
        final_response = ""

        async for event in executor.run(
            query=payload.content,
            model_name=payload.model,
            attachments=payload.attachments,
        ):
            if cancel_event.is_set():
                logger.info(f"Session {payload.session_id} cancelled.")
                return  # Exit early on cancellation

            match event:
                case ThoughtEvent(thought=t):
                    await conn.send(
                        {
                            "type": MessageType.THINKING.value,
                            "session_id": payload.session_id,
                            "data": {"type": "thought", "content": t},
                        }
                    )
                case ToolCallEvent(tool_name=n, tool_kwargs=k):
                    await conn.send(
                        {
                            "type": MessageType.THINKING.value,
                            "session_id": payload.session_id,
                            "data": {"type": "tool_call", "tool": n, "args": k},
                        }
                    )
                case ContentEvent(content=c):
                    await conn.send(
                        {
                            "type": MessageType.CONTENT_CHUNK.value,
                            "session_id": payload.session_id,
                            "content": c,
                        }
                    )
                case FinalResponseEvent(content=c):
                    final_response = c
                case ErrorEvent(error=e):
                    await conn.send_error(e, payload.session_id)
                case WarningEvent(warning=w):
                    await conn.send_warning(w, payload.session_id)
                case str(content):
                    final_response = content

        await conn.send(
            {
                "type": MessageType.MESSAGE.value,
                "session_id": payload.session_id,
                "content": final_response,
            }
        )

    except Exception as e:
        logger.exception("Error during chat processing")
        await conn.send_error(str(e), payload.session_id)
    finally:
        conn.cancel_events.pop(payload.session_id, None)


@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conn = ConnectionManager(websocket)

    try:
        while True:
            raw_data = await websocket.receive_json()

            try:
                payload = IncomingPayload(**raw_data)
            except ValidationError as e:
                await conn.send_error(f"Invalid payload: {e.errors()[0]['msg']}")
                continue
            match payload.type:
                case MessageType.PING:
                    await conn.send({"type": MessageType.PONG.value})
                case MessageType.CANCEL:
                    if payload.session_id:
                        conn.get_cancel_event(payload.session_id).set()
                case MessageType.MESSAGE:
                    conn.spawn_task(process_chat(payload, conn))

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        conn.cleanup()
