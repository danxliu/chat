import asyncio
import logging
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from storage import chat_storage
from models import AVAILABLE_MODELS
from workflow import (
    AgentExecutor,
    ContentEvent,
    ThoughtEvent,
    ToolCallEvent,
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

async def generate_title(session_id: str, query: str, websocket: WebSocket):
    if session_id in active_title_generations:
        return

    existing_title = await chat_storage.get_title(session_id)
    if existing_title and existing_title != "New Chat":
        return

    active_title_generations.add(session_id)
    try:
        executor = AgentExecutor(session_id)
        title = await executor.generate_title(query)
        if title:
            await websocket.send_json(
                {
                    "type": MessageType.TITLE_UPDATE,
                    "session_id": session_id,
                    "title": title,
                }
            )
    except Exception:
        logger.exception(f"Failed to generate title for session {session_id}")
    finally:
        active_title_generations.discard(session_id)

async def handle_message(
    payload: Dict[str, Any],
    websocket: WebSocket,
    cancel_events: Dict[str, asyncio.Event],
):
    session_id = payload.get("session_id")
    user_msg = payload.get("content")
    model_name = payload.get("model")

    if not session_id or not user_msg:
        return

    if not model_name or (AVAILABLE_MODELS and model_name not in AVAILABLE_MODELS):
        await websocket.send_json(
            {
                "type": MessageType.ERROR,
                "session_id": session_id,
                "message": f"Invalid or missing model: {model_name}",
            }
        )
        return

    executor = AgentExecutor(session_id)

    if session_id not in cancel_events:
        cancel_events[session_id] = asyncio.Event()
    cancel_events[session_id].clear()
    asyncio.create_task(generate_title(session_id, user_msg, websocket))

    try:
        handler = executor.run(query=user_msg, model_name=model_name)

        final_response = ""
        async for event in handler:
            if session_id in cancel_events and cancel_events[session_id].is_set():
                logger.info(f"Cancellation requested for session {session_id}")
                break

            match event:
                case ThoughtEvent(thought=thought):
                    await websocket.send_json(
                        {
                            "type": MessageType.THINKING,
                            "session_id": session_id,
                            "data": {"type": "thought", "content": thought},
                        }
                    )
                case ToolCallEvent(tool_name=name, tool_kwargs=kwargs):
                    await websocket.send_json(
                        {
                            "type": MessageType.THINKING,
                            "session_id": session_id,
                            "data": {"type": "tool_call", "tool": name, "args": kwargs},
                        }
                    )
                case ContentEvent(content=content):
                    await websocket.send_json(
                        {
                            "type": MessageType.CONTENT_CHUNK,
                            "session_id": session_id,
                            "content": content,
                        }
                    )
                case str(content):
                    final_response = content

        await websocket.send_json(
            {
                "type": MessageType.MESSAGE,
                "session_id": session_id,
                "content": final_response,
            }
        )
    except Exception as e:
        logger.exception("Error handling message")
        await websocket.send_json(
            {"type": MessageType.ERROR, "session_id": session_id, "message": str(e)}
        )

async def handle_ping(payload: Dict[str, Any], websocket: WebSocket, **kwargs):
    await websocket.send_json({"type": MessageType.PONG})

async def handle_cancel(
    payload: Dict[str, Any], cancel_events: Dict[str, asyncio.Event], **kwargs
):
    session_id = payload.get("session_id")
    if session_id and session_id in cancel_events:
        cancel_events[session_id].set()

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")

    cancel_events: Dict[str, asyncio.Event] = {}

    dispatcher: Dict[MessageType, Callable[..., Awaitable[None]]] = {
        MessageType.MESSAGE: handle_message,
        MessageType.PING: handle_ping,
        MessageType.CANCEL: handle_cancel,
    }

    async def run_handler(h: Callable[..., Awaitable[None]], **kwargs):
        try:
            await h(**kwargs)
        except Exception as e:
            logger.exception("Handler error")
            try:
                await websocket.send_json(
                    {
                        "type": MessageType.ERROR,
                        "session_id": kwargs.get("payload", {}).get("session_id"),
                        "message": f"Handler error: {str(e)}",
                    }
                )
            except:
                pass

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            handler = dispatcher.get(msg_type)

            if handler:
                asyncio.create_task(
                    run_handler(
                        handler,
                        payload=data,
                        websocket=websocket,
                        cancel_events=cancel_events,
                    )
                )
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                await websocket.send_json(
                    {
                        "type": MessageType.ERROR,
                        "message": f"Unknown message type: {msg_type}",
                    }
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await websocket.send_json({"type": MessageType.ERROR, "message": str(e)})
        except:
            pass
