from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Body, status, HTTPException
from src.schemas.schemas import SyncStatusResponse, SyncTriggerRequest, SyncTriggerResponse
from src.services.sync_service import SyncManager

sync_router = APIRouter(prefix="/sync", tags=["Sync"])


@sync_router.get(
    "/status",
    response_model=SyncStatusResponse,
    summary="Get automatic sync status",
    description="Retrieves current background sync status, scheduler state, last run stats, and next run time.",
)
def get_status() -> SyncStatusResponse:
    return SyncStatusResponse(**SyncManager.get_status())


@sync_router.post(
    "/trigger",
    response_model=SyncTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual banner sync",
    description="Asynchronously starts a banner scraping job in the background if no sync is currently running.",
)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    payload: Annotated[SyncTriggerRequest | None, Body(description="Optional sync configuration")] = None,
) -> SyncTriggerResponse:
    if SyncManager.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A banner sync job is already in progress.",
        )

    game_names = payload.game_names if payload else None
    download_images = payload.download_images if payload else None

    # Schedule non-blocking execution in background
    background_tasks.add_task(
        SyncManager.trigger_sync,
        game_names=game_names,
        download_images=download_images,
    )

    return SyncTriggerResponse(
        status="accepted",
        message="Banner sync job has been queued in background.",
        is_running=True,
    )
