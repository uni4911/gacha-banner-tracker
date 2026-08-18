from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.v1.router import api_v1_router
from src.config import IMAGES_DIR, ENABLE_SCHEDULER, RUN_SYNC_ON_STARTUP
from src.db.database import init_db
from src.services.sync_service import SyncManager, start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()

    # Start periodic background scraping via APScheduler
    if ENABLE_SCHEDULER:
        start_scheduler()
        if RUN_SYNC_ON_STARTUP:
            asyncio.create_task(SyncManager.trigger_sync())

    yield

    # Graceful shutdown of scheduler
    if ENABLE_SCHEDULER:
        shutdown_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gacha Banner Tracker API",
        description="API for tracking gacha banners across multiple games (Genshin Impact, Honkai: Star Rail, etc.)",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix="/api")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()
