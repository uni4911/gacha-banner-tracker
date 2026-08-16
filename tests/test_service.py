from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from src.db.models import Base, GameModel
from src.models.models import Banner, BannerType, Reward
import src.db.service as service


from sqlalchemy.pool import StaticPool


@pytest.fixture
def test_db(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(service, "SessionLocal", TestingSessionLocal)
    yield TestingSessionLocal


def test_get_or_create_game(test_db):
    with test_db() as session:
        # First call creates the game
        game1 = service.get_or_create_game(session, "Genshin Impact")
        session.commit()
        assert game1.id is not None
        assert game1.name == "Genshin Impact"

        # Second call returns the existing game
        game2 = service.get_or_create_game(session, "Genshin Impact")
        assert game2.id == game1.id

        # Verify only one game exists in the database
        games = session.scalars(select(GameModel)).all()
        assert len(games) == 1


def test_save_and_get_active_banners(test_db):
    start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 21, 23, 59, 59, tzinfo=timezone.utc)

    banner = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Mualani", rarity=5, is_featured=True)],
        low_rate_rewards=[Reward(name="Kachina", rarity=4, is_featured=False)],
        start_date=start,
        end_date=end,
        phase=1,
    )

    service.save_banners_to_db([banner], "Genshin Impact")

    # Query active banners during banner duration
    active_now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    active_banners = service.get_active_banners("Genshin Impact", active_now)

    assert len(active_banners) == 1
    assert active_banners[0].version == "5.0"
    assert active_banners[0].banner_type == BannerType.LIMITED_CHARACTER
    assert active_banners[0].limited_rewards[0].name == "Mualani"
    assert active_banners[0].low_rate_rewards[0].name == "Kachina"

    # Query when banner is expired
    future_time = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    expired_banners = service.get_active_banners("Genshin Impact", future_time)
    assert len(expired_banners) == 0


def test_get_upcoming_banners(test_db):
    start_future = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_future = datetime(2026, 6, 21, 18, 0, 0, tzinfo=timezone.utc)

    banner = Banner(
        version="5.2",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Chasca", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=start_future,
        end_date=end_future,
        phase=1,
    )

    service.save_banners_to_db([banner], "Genshin Impact")

    # Before banner start
    check_time = datetime(2026, 5, 15, 0, 0, 0, tzinfo=timezone.utc)
    upcoming = service.get_upcoming_banners("Genshin Impact", check_time)
    assert len(upcoming) == 1
    assert upcoming[0].limited_rewards[0].name == "Chasca"

    # After banner start
    after_time = datetime(2026, 6, 2, 0, 0, 0, tzinfo=timezone.utc)
    upcoming_after = service.get_upcoming_banners("Genshin Impact", after_time)
    assert len(upcoming_after) == 0


def test_get_character_banner_history(test_db):
    b1 = Banner(
        version="2.1",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Raiden Shogun", rarity=5, is_featured=True)],
        low_rate_rewards=[Reward(name="Kujou Sara", rarity=4, is_featured=False)],
        start_date=datetime(2021, 9, 1, tzinfo=timezone.utc),
        end_date=datetime(2021, 9, 21, tzinfo=timezone.utc),
        phase=1,
    )
    b2 = Banner(
        version="2.5",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Raiden Shogun", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2022, 3, 8, tzinfo=timezone.utc),
        end_date=datetime(2022, 3, 29, tzinfo=timezone.utc),
        phase=2,
    )
    b3 = Banner(
        version="2.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Ayaka", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2021, 7, 21, tzinfo=timezone.utc),
        end_date=datetime(2021, 8, 10, tzinfo=timezone.utc),
        phase=1,
    )

    service.save_banners_to_db([b1, b2, b3], "Genshin Impact")

    history = service.get_character_banner_history("Genshin Impact", "Raiden Shogun")
    assert len(history) == 2
    # Ordered by start_date desc
    assert history[0].version == "2.5"
    assert history[1].version == "2.1"


def test_get_banners_by_version(test_db):
    b1 = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Mualani", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 21, tzinfo=timezone.utc),
        phase=1,
    )
    b2 = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Kinich", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 1, 22, tzinfo=timezone.utc),
        end_date=datetime(2026, 2, 11, tzinfo=timezone.utc),
        phase=2,
    )
    b3 = Banner(
        version="5.1",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Xilonen", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 2, 12, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 4, tzinfo=timezone.utc),
        phase=1,
    )

    service.save_banners_to_db([b1, b2, b3], "Genshin Impact")

    v5_banners = service.get_banners_by_version("Genshin Impact", "5.0")
    assert len(v5_banners) == 2
    versions = [b.version for b in v5_banners]
    assert all(v == "5.0" for v in versions)

    v51_banners = service.get_banners_by_version("Genshin Impact", "5.1")
    assert len(v51_banners) == 1
    assert v51_banners[0].limited_rewards[0].name == "Xilonen"


def test_server_specific_active_banners(test_db):
    from src.models.models import Server

    # Phase 1 banner ending Jan 21, 2026 at 17:59:59 server time
    banner = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Mualani", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 1, 1, 6, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 21, 17, 59, 59, tzinfo=timezone.utc),
        phase=1,
    )
    service.save_banners_to_db([banner], "Genshin Impact")

    # At 2026-01-21 12:00:00 UTC:
    # Asia (UTC+8): 20:00:00 (Past 17:59:59 cutoff -> Expired)
    # Europe (Europe/Paris, UTC+1): 13:00:00 (Before 17:59:59 cutoff -> Active)
    # America (America/New_York, UTC-5): 07:00:00 (Before 17:59:59 cutoff -> Active)
    check_utc = datetime(2026, 1, 21, 12, 0, 0, tzinfo=timezone.utc)

    asia_active = service.get_active_banners("Genshin Impact", check_utc, server=Server.ASIA)
    europe_active = service.get_active_banners("Genshin Impact", check_utc, server=Server.EUROPE)
    america_active = service.get_active_banners("Genshin Impact", check_utc, server=Server.AMERICA)

    assert len(asia_active) == 0
    assert len(europe_active) == 1
    assert len(america_active) == 1


def test_get_all_games(test_db):
    with test_db() as session:
        service.get_or_create_game(session, "Honkai: Star Rail")
        service.get_or_create_game(session, "Genshin Impact")
        service.get_or_create_game(session, "Zenless Zone Zero")
        session.commit()

    games = service.get_all_games()
    assert len(games) == 3
    names = [g.name for g in games]
    assert "Genshin Impact" in names
    assert "Honkai: Star Rail" in names
    assert "Zenless Zone Zero" in names


def test_save_banners_duplicate_prevention(test_db):
    # First save with version "0.0" (e.g. initial / upcoming scrape)
    b1 = Banner(
        version="0.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Anaxa", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 8, 5, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 8, 25, 0, 0, 0, tzinfo=timezone.utc),
        phase=1,
    )
    service.save_banners_to_db([b1], "Honkai: Star Rail")

    active_1 = service.get_banners_by_version("Honkai: Star Rail", "0.0")
    assert len(active_1) == 1

    # Second save with version "4.4" for the same character and date range
    b2 = Banner(
        version="4.4",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Anaxa", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 8, 5, 18, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 8, 25, 14, 59, 59, tzinfo=timezone.utc),
        phase=2,
    )
    service.save_banners_to_db([b2], "Honkai: Star Rail")

    # Verify no duplicate was created and metadata was updated
    history = service.get_character_banner_history("Honkai: Star Rail", "Anaxa")
    assert len(history) == 1
    assert history[0].version == "4.4"
    assert history[0].phase == 2

