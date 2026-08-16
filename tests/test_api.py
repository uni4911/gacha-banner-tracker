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
def api_client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Patch SessionLocal and engine across service and database modules
    monkeypatch.setattr(service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(database, "engine", test_engine)

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

    resp = api_client.post("/games/Genshin%20Impact/banners", json=payload)
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
    api_client.post("/games/Genshin%20Impact/banners", json=payload)

    # Active time
    resp = api_client.get(
        "/games/Genshin%20Impact/banners/active",
        params={"current_time": "2026-01-10T12:00:00Z"},
    )
    assert resp.status_code == 200
    banners = resp.json()
    assert len(banners) == 1
    assert banners[0]["version"] == "5.0"
    assert banners[0]["limited_rewards"][0]["name"] == "Mualani"

    # Expired time
    resp_exp = api_client.get(
        "/games/Genshin%20Impact/banners/active",
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
    api_client.post("/games/Genshin%20Impact/banners", json=payload)

    resp = api_client.get(
        "/games/Genshin%20Impact/banners/upcoming",
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
    api_client.post("/games/Genshin%20Impact/banners", json=payload)

    resp = api_client.get("/games/Genshin%20Impact/banners/character/Raiden%20Shogun")
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
    api_client.post("/games/Genshin%20Impact/banners", json=payload)

    resp = api_client.get("/games/Genshin%20Impact/banners/version/5.0")
    assert resp.status_code == 200
    banners = resp.json()
    assert len(banners) == 1
    assert banners[0]["version"] == "5.0"


def test_v1_prefixed_endpoints(api_client):
    # Test /api/v1/games/{game_name}/banners routes
    resp_banners = api_client.post(
        "/api/v1/games/Star%20Rail/banners",
        json=[
            {
                "version": "2.0",
                "phase": 1,
                "banner_type": "LIMITED_CHARACTER",
                "start_date": "2026-02-01T10:00:00Z",
                "end_date": "2026-02-21T18:00:00Z",
                "limited_rewards": [
                    {"name": "Black Swan", "rarity": 5, "is_featured": True}
                ],
            }
        ],
    )
    assert resp_banners.status_code == 201

    resp_active = api_client.get(
        "/api/v1/games/Star%20Rail/banners/active",
        params={"current_time": "2026-02-10T12:00:00Z"},
    )
    assert resp_active.status_code == 200
    assert len(resp_active.json()) == 1


def test_active_banners_with_server_region_param(api_client):
    # Phase 1 banner ending Jan 21, 2026 at 17:59:59 server time
    payload = [
        {
            "version": "5.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T06:00:00Z",
            "end_date": "2026-01-21T17:59:59Z",
            "limited_rewards": [
                {"name": "Mualani", "rarity": 5, "is_featured": True}
            ],
        }
    ]
    api_client.post("/games/Genshin%20Impact/banners", json=payload)

    # At 2026-01-21 12:00:00 UTC (past Asia 17:59 cutoff, but active in Europe and America)
    check_time = "2026-01-21T12:00:00Z"

    resp_asia = api_client.get(
        "/games/Genshin%20Impact/banners/active",
        params={"current_time": check_time, "server": "ASIA"},
    )
    assert resp_asia.status_code == 200
    assert len(resp_asia.json()) == 0

    resp_eu = api_client.get(
        "/games/Genshin%20Impact/banners/active",
        params={"current_time": check_time, "server": "EUROPE"},
    )
    assert resp_eu.status_code == 200
    assert len(resp_eu.json()) == 1

    resp_na = api_client.get(
        "/games/Genshin%20Impact/banners/active",
        params={"current_time": check_time, "server": "AMERICA"},
    )
    assert resp_na.status_code == 200
    assert len(resp_na.json()) == 1

    # Test IANA timezone string inputs also succeed without 422
    resp_iana_eu = api_client.get(
        "/games/Genshin%20Impact/banners/active",
        params={"current_time": check_time, "server": "Europe/Paris"},
    )
    assert resp_iana_eu.status_code == 200
    assert len(resp_iana_eu.json()) == 1

    resp_iana_asia = api_client.get(
        "/games/Genshin%20Impact/banners/active",
        params={"current_time": check_time, "server": "Asia/Shanghai"},
    )
    assert resp_iana_asia.status_code == 200
    assert len(resp_iana_asia.json()) == 0


def test_list_games_endpoint(api_client):
    # Post a banner for Genshin Impact and a banner for Star Rail
    api_client.post(
        "/games/Genshin%20Impact/banners",
        json=[{
            "version": "5.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T06:00:00Z",
            "limited_rewards": [{"name": "Mualani", "rarity": 5, "is_featured": True}],
        }],
    )
    api_client.post(
        "/games/Zenless%20Zone%20Zero/banners",
        json=[{
            "version": "1.0",
            "phase": 1,
            "banner_type": "LIMITED_CHARACTER",
            "start_date": "2026-01-01T06:00:00Z",
            "limited_rewards": [{"name": "Ellen Joe", "rarity": 5, "is_featured": True}],
        }],
    )

    resp = api_client.get("/games")
    assert resp.status_code == 200
    games = resp.json()
    assert len(games) >= 2
    game_names = [g["name"] for g in games]
    assert "Genshin Impact" in game_names
    assert "Zenless Zone Zero" in game_names

    resp_v1 = api_client.get("/api/v1/games")
    assert resp_v1.status_code == 200
    assert len(resp_v1.json()) == len(games)

