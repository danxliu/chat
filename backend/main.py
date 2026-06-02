import logging
from contextlib import asynccontextmanager

import uvicorn
from api import api_router
from config import settings
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI()

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
    app.mount("/", StaticFiles(directory=str(settings.FRONTEND_BUILD_DIR)), name="ui")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
