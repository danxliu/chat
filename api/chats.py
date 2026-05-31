import uuid

from fastapi import APIRouter

from models import AVAILABLE_MODELS
from storage import chat_storage
from workflow import AgentExecutor

router = APIRouter(prefix="/api/chats")


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


@router.get("/models")
async def list_models():
    return {"models": AVAILABLE_MODELS}
