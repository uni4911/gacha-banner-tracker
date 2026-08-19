
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from src.db.models import Base
import src.db.service as service
import src.db.database as database
from src.api.app import app


@pytest.fixture
def api_client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_check(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_banners_endpoint(api_client):
    payload = [
        {
            "version": "5.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T10:00:00Z",
            "end_date": "2026-01-21T18:00:00Z",
            "rewards": [
                {"name": "Mualani", "rarity": 5, "is_featured": True, "extra_data": {}},
                {"name": "Kachina", "rarity": 4, "is_featured": False, "extra_data": {}},
            ],
        },
        {
            "version": "5.0",
            "phase": 2,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-22T10:00:00Z",
            "end_date": "2026-02-11T18:00:00Z",
            "limited_rewards": [
                {"name": "Kinich", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [
                {"name": "Chevreuse", "rarity": 4, "is_featured": False, "extra_data": {}}
            ],
        },
    ]

    resp = api_client.post("/api/v1/games/Genshin%20Impact/banners", json=payload)
    assert resp.status_code == 201
    assert resp.json()["count"] == 2


def test_get_active_banners_endpoint(api_client):
    payload = [
        {
            "version": "5.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T10:00:00Z",
            "end_date": "2026-01-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Mualani", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [
                {"name": "Kachina", "rarity": 4, "is_featured": False, "extra_data": {}}
            ],
        }
    ]
    api_client.post("/api/v1/games/Genshin%20Impact/banners", json=payload)

    # Active time
    resp = api_client.get(
        "/api/v1/games/Genshin%20Impact/banners/active",
        params={"current_time": "2026-01-10T12:00:00Z"},
    )
    assert resp.status_code == 200
    banners = resp.json()
    assert len(banners) == 1
    assert banners[0]["version"] == "5.0"
    assert banners[0]["limited_rewards"][0]["name"] == "Mualani"

    # Expired time
    resp_exp = api_client.get(
        "/api/v1/games/Genshin%20Impact/banners/active",
        params={"current_time": "2026-02-01T00:00:00Z"},
    )
    assert resp_exp.status_code == 200
    assert len(resp_exp.json()) == 0


def test_get_upcoming_banners_endpoint(api_client):
    payload = [
        {
            "version": "5.3",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-06-01T10:00:00Z",
            "end_date": "2026-06-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Mavuika", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        }
    ]
    api_client.post("/api/v1/games/Genshin%20Impact/banners", json=payload)

    resp = api_client.get(
        "/api/v1/games/Genshin%20Impact/banners/upcoming",
        params={"current_time": "2026-05-01T00:00:00Z"},
    )
    assert resp.status_code == 200
    banners = resp.json()
    assert len(banners) == 1
    assert banners[0]["limited_rewards"][0]["name"] == "Mavuika"


def test_get_character_history_endpoint(api_client):
    payload = [
        {
            "version": "2.1",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2021-09-01T10:00:00Z",
            "end_date": "2021-09-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Raiden Shogun", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        },
        {
            "version": "3.3",
            "phase": 2,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2022-12-27T10:00:00Z",
            "end_date": "2023-01-17T18:00:00Z",
            "limited_rewards": [
                {"name": "Raiden Shogun", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        },
    ]
    api_client.post("/api/v1/games/Genshin%20Impact/banners", json=payload)

    resp = api_client.get("/api/v1/games/Genshin%20Impact/banners/character/Raiden%20Shogun")
    assert resp.status_code == 200
    banners = resp.json()
    assert len(banners) == 2
    assert banners[0]["version"] == "3.3"
    assert banners[1]["version"] == "2.1"


def test_get_version_banners_endpoint(api_client):
    payload = [
        {
            "version": "5.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T10:00:00Z",
            "end_date": "2026-01-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Mualani", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        }
    ]
    api_client.post("/api/v1/games/Genshin%20Impact/banners", json=payload)

    resp = api_client.get("/api/v1/games/Genshin%20Impact/banners/version/5.0")
    assert resp.status_code == 200
    banners = resp.json()
    assert len(banners) == 1
    assert banners[0]["version"] == "5.0"


def test_get_all_games_endpoint(api_client):
    payload = [
        {
            "version": "1.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T10:00:00Z",
            "end_date": "2026-01-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Rover", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        }
    ]
    api_client.post("/api/v1/games/Wuthering%20Waves/banners", json=payload)

    resp = api_client.get("/api/v1/games")
    assert resp.status_code == 200
    games = resp.json()
    assert any(g["name"] == "Wuthering Waves" for g in games)


def test_no_unprefixed_duplicate_routes(api_client):
    # Verify that un-prefixed /games routes are no longer exposed on root
    resp = api_client.get("/games")
    assert resp.status_code == 404


def test_list_banners_endpoint_with_slug_and_pagination(api_client):
    payload = [
        {
            "version": "5.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T10:00:00Z",
            "end_date": "2026-01-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Mualani", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        },
        {
            "version": "5.0",
            "phase": 2,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-22T10:00:00Z",
            "end_date": "2026-02-11T18:00:00Z",
            "limited_rewards": [
                {"name": "Kinich", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        },
    ]
    # Post banners with full game name
    api_client.post("/api/v1/games/Genshin%20Impact/banners", json=payload)

    # Query with slug 'genshin-impact'
    resp = api_client.get("/api/v1/games/genshin-impact/banners?page=1&page_size=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total_pages"] == 2
    assert len(data["items"]) == 1


def test_list_banners_endpoint_with_filters(api_client):
    payload = [
        {
            "version": "5.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T10:00:00Z",
            "end_date": "2026-01-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Mualani", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        },
        {
            "version": "5.1",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-06-01T10:00:00Z",
            "end_date": "2026-06-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Xilonen", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        },
    ]
    api_client.post("/api/v1/games/genshin-impact/banners", json=payload)

    # Filter by character name
    resp_char = api_client.get("/api/v1/games/genshin-impact/banners?character=Xilonen")
    assert resp_char.status_code == 200
    data_char = resp_char.json()
    assert data_char["total"] == 1
    assert data_char["items"][0]["limited_rewards"][0]["name"] == "Xilonen"

    # Filter by active status at Jan 10, 2026
    resp_active = api_client.get(
        "/api/v1/games/genshin-impact/banners?status=active&current_time=2026-01-10T12:00:00Z"
    )
    assert resp_active.status_code == 200
    data_active = resp_active.json()
    assert data_active["total"] == 1
    assert data_active["items"][0]["limited_rewards"][0]["name"] == "Mualani"


def test_get_single_game_detail_endpoint(api_client):
    payload = [
        {
            "version": "1.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T10:00:00Z",
            "end_date": "2026-01-21T18:00:00Z",
            "limited_rewards": [
                {"name": "Rover", "rarity": 5, "is_featured": True, "extra_data": {}}
            ],
            "low_rate_rewards": [],
        }
    ]
    api_client.post("/api/v1/games/wuthering-waves/banners", json=payload)

    # Query by slug
    resp = api_client.get("/api/v1/games/wuthering-waves")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "wuthering-waves"
    assert data["slug"] == "wuthering-waves"

    # Query non-existent game -> 404
    resp_404 = api_client.get("/api/v1/games/non-existent-game-slug")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()

