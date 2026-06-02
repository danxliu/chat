import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from memory import reset_memory
from models import AVAILABLE_MODELS
from storage import chat_storage
from workflow import AgentExecutor
from config import settings

router = APIRouter(prefix="/api/chats")

UPLOAD_DIR = settings.UPLOADS_DIR
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("")
async def create_chat():
    session_id = str(uuid.uuid4())
    await chat_storage.save_context(
        session_id,
        {
            "chat_history": [],
            "metadata": {"session_id": session_id},
        },
    )
    return {"session_id": session_id}


@router.get("")
async def list_chats():
    sessions = await chat_storage.list_sessions_with_titles()
    return {"sessions": sessions}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix if file.filename else ""
        stored_filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / stored_filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "file_id": file_id,
            "filename": file.filename,
            "mime_type": file.content_type,
            "stored_filename": stored_filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/models")
async def list_models():
    return {"models": AVAILABLE_MODELS}


@router.delete("/memory")
async def clear_memory():
    reset_memory()
    return {"status": "success"}


@router.get("/{session_id}/history")
async def get_chat_history(session_id: str):
    executor = AgentExecutor(session_id)
    history = await executor.get_history()
    return {"history": history}


@router.delete("/{session_id}")
async def delete_chat(session_id: str):
    await chat_storage.delete_context(session_id)
    return {"status": "success"}


@router.delete("")
async def clear_all_chats():
    await chat_storage.clear_all()
    return {"status": "success"}
