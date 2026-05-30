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

from workflow import AgentExecutor, ThoughtEvent, ToolCallEvent
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
    # State is initialized on first use in AgentExecutor, or we can save an empty one
    await chat_storage.save_context(session_id, {
        "chat_history": [],
        "metadata": {"session_id": session_id},
        "continuation_number": 0,
        "continue_task": False,
        "session_summary": ""
    })
    return {"session_id": session_id}


@app.get("/api/chats")
async def list_chats():
    sessions = await chat_storage.list_sessions_with_titles()
    return {"sessions": sessions}


@app.get("/api/chats/{session_id}/history")
async def get_chat_history(session_id: str):
    executor = AgentExecutor(session_id)
    history = await executor.get_history()
    return {"history": history}


@app.delete("/api/chats/{session_id}")
async def delete_chat(session_id: str):
    await chat_storage.delete_context(session_id)
    return {"status": "success"}


@app.delete("/api/chats")
async def clear_all_chats():
    await chat_storage.clear_all()
    return {"status": "success"}


async def handle_message(payload: Dict[str, Any], websocket: WebSocket, cancel_events: Dict[str, asyncio.Event]):
    session_id = payload.get("session_id")
    user_msg = payload.get("content")
    
    if not session_id or not user_msg:
        return
        
    executor = AgentExecutor(session_id)
    
    # Setup cancellation event for this session
    if session_id not in cancel_events:
        cancel_events[session_id] = asyncio.Event()
    cancel_events[session_id].clear()
    
    try:
        handler = executor.run(query=user_msg)
        
        final_response = ""
        async for event in handler:
            if isinstance(event, ThoughtEvent):
                await websocket.send_json({
                    "type": MessageType.THINKING,
                    "session_id": session_id,
                    "data": {"type": "thought", "content": event.thought}
                })
            elif isinstance(event, ToolCallEvent):
                await websocket.send_json({
                    "type": MessageType.THINKING,
                    "session_id": session_id,
                    "data": {
                        "type": "tool_call",
                        "tool": event.tool_name,
                        "args": event.tool_kwargs
                    }
                })
            elif isinstance(event, str):
                final_response = event
        
        await websocket.send_json({
            "type": MessageType.MESSAGE,
            "session_id": session_id,
            "content": final_response
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
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
            import traceback
            traceback.print_exc()
            try:
                await websocket.send_json({
                    "type": MessageType.ERROR,
                    "session_id": kwargs.get("payload", {}).get("session_id"),
                    "message": f"Handler error: {str(e)}"
                })
            except:
                pass

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            handler = dispatcher.get(msg_type)
            
            if handler:
                # Run handler as a task to allow concurrent processing
                asyncio.create_task(run_handler(handler, payload=data, websocket=websocket, cancel_events=cancel_events))
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
