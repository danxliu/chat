import asyncio
import os
import uuid
import json
from enum import Enum
from typing import Dict, Any, Callable, Awaitable

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from llama_index.core.workflow import Context

from agent import InfiniteAgentWorkflow
from storage import chat_storage

app = FastAPI()

# Mount the static directory to serve frontend assets
app.mount("/static", StaticFiles(directory="static"), name="static")


class MessageType(str, Enum):
    # Active Chat Loop
    MESSAGE = "message"
    THINKING = "thinking"
    PING = "ping"
    PONG = "pong"
    CANCEL = "cancel"
    ERROR = "error"


@app.get("/")
async def get_index():
    return FileResponse("static/index.html")


@app.post("/api/chats")
async def create_chat():
    session_id = str(uuid.uuid4())
    workflow = InfiniteAgentWorkflow(timeout=3600.0)
    ctx = Context(workflow)
    await ctx.set("session_id", session_id)
    await chat_storage.save_context(session_id, ctx)
    return {"session_id": session_id}


@app.get("/api/chats")
async def list_chats():
    sessions = await chat_storage.list_sessions()
    return {"sessions": sessions}


@app.get("/api/chats/{session_id}/history")
async def get_chat_history(session_id: str):
    workflow = InfiniteAgentWorkflow(timeout=3600.0)
    ctx = await chat_storage.load_context(session_id, workflow)
    if not ctx:
        return {"history": []}

    history_dicts = await ctx.get("chat_history", default=[])
    history = []
    for msg in history_dicts:
        role = msg.get("role")
        role_str = role.value if hasattr(role, "value") else str(role)
        if "MessageRole." in role_str:
            role_str = role_str.split(".")[-1].lower()
        
        history.append({
            "role": role_str,
            "content": msg.get("content")
        })

    return {"history": history}


@app.delete("/api/chats/{session_id}")
async def delete_chat(session_id: str):
    await chat_storage.delete_context(session_id)
    return {"status": "success"}


async def handle_message(payload: Dict[str, Any], websocket: WebSocket, workflow: InfiniteAgentWorkflow, cancel_events: Dict[str, asyncio.Event]):
    session_id = payload.get("session_id")
    user_msg = payload.get("content")
    
    if not session_id or not user_msg:
        return
        
    ctx = await chat_storage.load_context(session_id, workflow)
    if not ctx:
        await websocket.send_json({"type": MessageType.ERROR, "message": "Session not found."})
        return

    # Setup cancellation event for this session
    if session_id not in cancel_events:
        cancel_events[session_id] = asyncio.Event()
    cancel_events[session_id].clear()
    
    # Simple "thinking" indicator
    await websocket.send_json({"type": MessageType.THINKING, "session_id": session_id, "content": "Assistant is thinking..."})
    
    try:
        # Note: True cancellation requires wrapping workflow.run in a task and waiting on both it and the event
        response = await workflow.run(query=user_msg, ctx=ctx)
        await chat_storage.save_context(session_id, ctx)
        await websocket.send_json({
            "type": MessageType.MESSAGE,
            "session_id": session_id,
            "content": str(response)
        })
    except Exception as e:
        await websocket.send_json({"type": MessageType.ERROR, "session_id": session_id, "message": str(e)})


async def handle_ping(payload: Dict[str, Any], websocket: WebSocket, **kwargs):
    await websocket.send_json({"type": MessageType.PONG})


async def handle_cancel(payload: Dict[str, Any], cancel_events: Dict[str, asyncio.Event], **kwargs):
    session_id = payload.get("session_id")
    if session_id and session_id in cancel_events:
        cancel_events[session_id].set()


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Persistent WebSocket connection established")

    workflow = InfiniteAgentWorkflow(timeout=3600.0)
    cancel_events: Dict[str, asyncio.Event] = {}

    dispatcher: Dict[MessageType, Callable[..., Awaitable[None]]] = {
        MessageType.MESSAGE: handle_message,
        MessageType.PING: handle_ping,
        MessageType.CANCEL: handle_cancel,
    }

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            handler = dispatcher.get(msg_type)
            
            if handler:
                # Run handler as a task to allow concurrent processing (multiple sessions or heartbeats)
                asyncio.create_task(handler(payload=data, websocket=websocket, workflow=workflow, cancel_events=cancel_events))
            else:
                print(f"Unknown message type: {msg_type}")
                await websocket.send_json({"type": MessageType.ERROR, "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({"type": MessageType.ERROR, "message": str(e)})
        except:
            pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
