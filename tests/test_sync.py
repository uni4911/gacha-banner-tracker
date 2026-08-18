from __future__ import annotations
import asyncio
import time
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.services.sync_service import (
    SyncManager,
    start_scheduler,
    shutdown_scheduler,
    get_scheduler,
)


@pytest.fixture(autouse=True)
def reset_sync_state():
    """Reset SyncManager state and shutdown scheduler before and after each test."""
    SyncManager.is_running = False
    SyncManager.last_status = "idle"
    SyncManager.last_synced_at = None
    SyncManager.last_duration_seconds = None
    SyncManager.last_error = None
    SyncManager.last_results = None
    shutdown_scheduler()
    yield
    SyncManager.is_running = False
    shutdown_scheduler()


def test_sync_status_initial():
    status = SyncManager.get_status()
    assert status["is_running"] is False
    assert status["status"] == "idle"
    assert status["last_synced_at"] is None
    assert status["last_error"] is None
    assert status["scheduler_active"] is False


@pytest.mark.anyio
async def test_sync_manager_trigger_sync_success():
    mock_results = {"Genshin Impact": 4, "Honkai: Star Rail": 2}
    with patch("src.services.sync_service.run_pipeline", return_value=mock_results) as mock_run:
        result = await SyncManager.trigger_sync(download_images=False)

        mock_run.assert_called_once_with(
            game_names=None,
            download_images_locally=False,
        )
        assert result["status"] == "success"
        assert result["is_running"] is False
        assert result["results"] == mock_results
        assert SyncManager.last_status == "success"
        assert SyncManager.last_synced_at is not None
        assert SyncManager.last_error is None


@pytest.mark.anyio
async def test_sync_manager_trigger_sync_error():
    with patch("src.services.sync_service.run_pipeline", side_effect=RuntimeError("Network Timeout")):
        result = await SyncManager.trigger_sync()

        assert result["status"] == "error"
        assert "Network Timeout" in result["error"]
        assert SyncManager.last_status == "error"
        assert SyncManager.last_error == "Network Timeout"
        assert SyncManager.is_running is False


@pytest.mark.anyio
async def test_sync_manager_concurrency_lock():
    def slow_pipeline(**kwargs):
        time.sleep(0.08)
        return {"Genshin Impact": 1}

    with patch("src.services.sync_service.run_pipeline", side_effect=slow_pipeline):
        task1 = asyncio.create_task(SyncManager.trigger_sync())
        await asyncio.sleep(0.02)

        # Attempt to trigger while task1 is in progress
        busy_result = await SyncManager.trigger_sync()
        assert busy_result["status"] == "busy"
        assert busy_result["is_running"] is True

        res1 = await task1
        assert res1["status"] == "success"


def test_api_sync_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_running" in data
    assert "status" in data
    assert "scheduler_active" in data
    assert data["status"] == "idle"


def test_api_sync_trigger_endpoint():
    client = TestClient(app)
    with patch("src.services.sync_service.run_pipeline", return_value={"Genshin Impact": 2}):
        response = client.post(
            "/api/v1/sync/trigger",
            json={"game_names": ["Genshin Impact"], "download_images": False},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["is_running"] is True


def test_api_sync_trigger_conflict():
    client = TestClient(app)
    SyncManager.is_running = True
    try:
        response = client.post("/api/v1/sync/trigger", json={})
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]
    finally:
        SyncManager.is_running = False


@pytest.mark.anyio
async def test_scheduler_start_and_shutdown():
    with patch("src.services.sync_service.ENABLE_SCHEDULER", True):
        start_scheduler()
        sched = get_scheduler()
        assert sched.running is True

        job = sched.get_job("auto_fetch_banners_job")
        assert job is not None
        assert job.name == "Periodic Banner Scrape Job"

        status = SyncManager.get_status()
        assert status["scheduler_active"] is True
        assert status["next_run_time"] is not None

        shutdown_scheduler()
        await asyncio.sleep(0)
        assert sched.running is False
