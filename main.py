import asyncio
import os
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from agent import InfiniteAgentWorkflow

app = FastAPI()

# Mount the static directory to serve frontend assets
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("static/index.html")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Initialize the workflow. 
    # Note: For a persistent chat session, we might want to store state,
    # but for now, each workflow.run handles the multi-step reasoning for one query.
    workflow = InfiniteAgentWorkflow(timeout=3600.0)
    
    try:
        while True:
            # Receive user message
            user_msg = await websocket.receive_text()
            
            # Run the agent workflow
            # This will process the query, potentially running multiple loops/tools
            response = await workflow.run(query=user_msg)
            
            # Send the result back to the user
            await websocket.send_text(str(response))
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in websocket loop: {e}")
        await websocket.send_text(f"Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
