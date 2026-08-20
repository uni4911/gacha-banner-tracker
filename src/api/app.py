from __future__ import annotations
import asyncio
import os
import shutil
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.api.v1.router import api_v1_router
from src.config import IMAGES_DIR, DATA_DIR, ENABLE_SCHEDULER, RUN_SYNC_ON_STARTUP
from src.db.database import get_db, init_db
from src.schemas.schemas import HealthResponse, DatabaseHealth, StorageHealth
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

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Deep health check",
        description="Performs active diagnostics on database connectivity, latency, disk storage, and scheduler status.",
    )
    def health_check(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
        # 1. Database connectivity & latency
        db_status = "healthy"
        db_latency: float | None = None
        db_error: str | None = None
        try:
            t0 = time.perf_counter()
            db.execute(text("SELECT 1"))
            db_latency = round((time.perf_counter() - t0) * 1000, 2)
        except Exception as exc:
            db_status = "unhealthy"
            db_error = str(exc)

        # 2. Disk & Image Storage check
        storage_status = "healthy"
        images_dir_writable = False
        cached_images_count = 0
        cache_size_bytes = 0
        free_disk_gb: float | None = None
        storage_error: str | None = None

        try:
            IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            images_dir_writable = os.access(str(IMAGES_DIR), os.W_OK)
            if not images_dir_writable:
                storage_status = "degraded"

            if IMAGES_DIR.exists():
                for p in IMAGES_DIR.rglob("*"):
                    if p.is_file():
                        cached_images_count += 1
                        cache_size_bytes += p.stat().st_size

            if DATA_DIR.exists():
                disk_info = shutil.disk_usage(str(DATA_DIR))
                free_disk_gb = round(disk_info.free / (1024 ** 3), 2)
        except Exception as exc:
            storage_status = "unhealthy"
            storage_error = str(exc)

        cache_size_mb = round(cache_size_bytes / (1024 * 1024), 2)

        # 3. Scheduler & Sync status
        sync_status = SyncManager.get_status()
        scheduler_active = sync_status.get("scheduler_active", False)
        is_sync_running = sync_status.get("is_running", False)

        # 4. Overall status
        if db_status == "unhealthy":
            overall_status = "unhealthy"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif storage_status != "healthy":
            overall_status = "degraded"
        else:
            overall_status = "ok"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            database=DatabaseHealth(
                status=db_status,
                latency_ms=db_latency,
                error=db_error,
            ),
            storage=StorageHealth(
                status=storage_status,
                images_dir_writable=images_dir_writable,
                cached_images_count=cached_images_count,
                cache_size_mb=cache_size_mb,
                free_disk_gb=free_disk_gb,
                error=storage_error,
            ),
            scheduler_active=scheduler_active,
            is_sync_running=is_sync_running,
        )

    return app



app = create_app()
