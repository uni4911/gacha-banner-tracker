from __future__ import annotations
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import (
    FETCH_INTERVAL_HOURS,
    DOWNLOAD_IMAGES_LOCALLY,
    ENABLE_SCHEDULER,
)
from src.services.pipeline import run_pipeline

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None
_sync_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _sync_lock
    if _sync_lock is None:
        _sync_lock = asyncio.Lock()
    return _sync_lock


class SyncManager:
    is_running: bool = False
    last_status: str = "idle"  # "idle" | "running" | "success" | "error"
    last_synced_at: datetime | None = None
    last_duration_seconds: float | None = None
    last_error: str | None = None
    last_results: dict[str, int] | None = None

    @classmethod
    async def trigger_sync(
        cls,
        game_names: list[str] | None = None,
        download_images: bool | None = None,
    ) -> dict[str, Any]:
        """
        Executes the scraping pipeline safely in a background worker thread with concurrency locking.
        """
        lock = _get_lock()
        if lock.locked() or cls.is_running:
            return {
                "status": "busy",
                "message": "A sync operation is already in progress.",
                "is_running": True,
            }

        async with lock:
            cls.is_running = True
            cls.last_status = "running"
            cls.last_error = None
            start_ts = time.perf_counter()

            should_download_images = (
                download_images if download_images is not None else DOWNLOAD_IMAGES_LOCALLY
            )

            try:
                logger.info("Starting automatic/manual banner sync...")
                # Run the blocking network / parsing pipeline in a separate thread
                results = await asyncio.to_thread(
                    run_pipeline,
                    game_names=game_names,
                    download_images_locally=should_download_images,
                )
                cls.last_results = results
                cls.last_synced_at = datetime.now(timezone.utc)
                cls.last_status = "success"
                cls.last_duration_seconds = round(time.perf_counter() - start_ts, 2)
                logger.info(
                    f"Banner sync completed successfully in {cls.last_duration_seconds}s. Results: {results}"
                )
                return {
                    "status": "success",
                    "message": "Sync completed successfully.",
                    "is_running": False,
                    "last_synced_at": cls.last_synced_at.isoformat(),
                    "duration_seconds": cls.last_duration_seconds,
                    "results": cls.last_results,
                }
            except Exception as exc:
                cls.last_status = "error"
                cls.last_error = str(exc)
                cls.last_duration_seconds = round(time.perf_counter() - start_ts, 2)
                logger.error(f"Banner sync failed: {exc}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"Sync failed: {exc}",
                    "is_running": False,
                    "error": str(exc),
                    "duration_seconds": cls.last_duration_seconds,
                }
            finally:
                cls.is_running = False

    @classmethod
    def get_status(cls) -> dict[str, Any]:
        """
        Returns full diagnostic status of the sync system and scheduler.
        """
        next_run_time: datetime | None = None
        scheduler_active = False

        if _scheduler is not None and _scheduler.running:
            scheduler_active = True
            job = _scheduler.get_job("auto_fetch_banners_job")
            if job and job.next_run_time:
                next_run_time = job.next_run_time

        return {
            "is_running": cls.is_running,
            "status": cls.last_status,
            "last_synced_at": cls.last_synced_at,
            "next_run_time": next_run_time,
            "last_duration_seconds": cls.last_duration_seconds,
            "last_error": cls.last_error,
            "last_results": cls.last_results,
            "scheduler_active": scheduler_active,
        }


async def _scheduled_sync_job() -> None:
    """Invoked periodically by APScheduler."""
    logger.info("Executing scheduled banner sync job via APScheduler...")
    await SyncManager.trigger_sync()


def get_scheduler() -> AsyncIOScheduler:
    """Returns or initializes the global AsyncIOScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def start_scheduler(event_loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Configures and starts the periodic banner fetch scheduler."""
    if not ENABLE_SCHEDULER:
        logger.info("APScheduler is disabled via configuration.")
        return

    sched = get_scheduler()
    if event_loop is not None:
        sched._eventloop = event_loop

    if not sched.running:
        sched.add_job(
            _scheduled_sync_job,
            trigger=IntervalTrigger(hours=FETCH_INTERVAL_HOURS),
            id="auto_fetch_banners_job",
            name="Periodic Banner Scrape Job",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        sched.start()
        logger.info(
            f"APScheduler started successfully. Banner fetch scheduled every {FETCH_INTERVAL_HOURS} hour(s)."
        )


def shutdown_scheduler() -> None:
    """Gracefully shuts down the background scheduler."""
    global _scheduler
    if _scheduler is not None:
        if _scheduler.running:
            _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler shut down successfully.")

