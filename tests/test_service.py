from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base
from src.models.models import Banner, BannerType, Reward
import src.db.service as service


@pytest.fixture
def test_db(monkeypatch):
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(service, "SessionLocal", TestingSessionLocal)
    yield TestingSessionLocal


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
