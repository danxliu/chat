from fastapi import APIRouter
from .chats import router as chats_router
from .websockets import router as websockets_router

api_router = APIRouter()
api_router.include_router(chats_router)
api_router.include_router(websockets_router)
