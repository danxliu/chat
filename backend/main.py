import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import api_router
from config import settings
from models import refresh_models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await refresh_models()
    yield


app = FastAPI(lifespan=lifespan)

# Ensure uploads directory exists
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(settings.UPLOADS_DIR)), name="uploads")

app.include_router(api_router)


@app.get("/")
async def get_index():
    index_path = settings.FRONTEND_BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "Frontend not built yet. Run 'bun run build' in the frontend directory."
    }


if settings.FRONTEND_BUILD_DIR.exists():
    # Mount SvelteKit build assets separately so API routes take priority
    assets_dir = settings.FRONTEND_BUILD_DIR / "_app"
    if assets_dir.exists():
        app.mount("/_app", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = settings.FRONTEND_BUILD_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(settings.FRONTEND_BUILD_DIR / "index.html"))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
