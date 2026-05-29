import asyncio
import os

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


@app.get("/")
async def get_index():
    return FileResponse("static/index.html")


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = websocket.query_params.get("session_id", "default_session")

    workflow = InfiniteAgentWorkflow(timeout=3600.0)
    ctx = await chat_storage.load_context(session_id, workflow)

    if ctx is None:
        ctx = Context(workflow)
        await ctx.set("session_id", session_id)

    try:
        while True:
            user_msg = await websocket.receive_text()
            response = await workflow.run(query=user_msg, ctx=ctx)
            await chat_storage.save_context(session_id, ctx)
            await websocket.send_text(str(response))
    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
    except Exception as e:
        print(f"Error in websocket loop: {e}")
        await websocket.send_text(f"Error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
