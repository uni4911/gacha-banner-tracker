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


def test_sql_level_active_filtering_with_permanent_and_expired(test_db):
    # 1. Expired banner (year 2021)
    b_expired = Banner(
        version="1.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Venti", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2021, 1, 21, 0, 0, 0, tzinfo=timezone.utc),
        phase=1,
    )
    # 2. Currently active limited banner (year 2026)
    b_active = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Mualani", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 8, 25, 0, 0, 0, tzinfo=timezone.utc),
        phase=1,
    )
    # 3. Permanent standard banner (no end date)
    b_permanent = Banner(
        version="1.0",
        banner_type=BannerType.STANDARD_CHARACTER,
        limited_rewards=[Reward(name="Standard Pool", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2020, 9, 28, 0, 0, 0, tzinfo=timezone.utc),
        end_date=None,
        phase=1,
    )
    # 4. Far future upcoming banner (year 2027)
    b_future = Banner(
        version="6.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Future Hero", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2027, 1, 21, 0, 0, 0, tzinfo=timezone.utc),
        phase=1,
    )

    service.save_banners_to_db([b_expired, b_active, b_permanent, b_future], "Genshin Impact")

    # Query active banners at Aug 15, 2026
    current_time = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    active = service.get_active_banners("Genshin Impact", current_time)

    assert len(active) == 2
    active_names = [b.limited_rewards[0].name for b in active]
    assert "Mualani" in active_names
    assert "Standard Pool" in active_names
    assert "Venti" not in active_names
    assert "Future Hero" not in active_names

    # Query upcoming banners at Aug 15, 2026
    upcoming = service.get_upcoming_banners("Genshin Impact", current_time)
    assert len(upcoming) == 1
    assert upcoming[0].limited_rewards[0].name == "Future Hero"


def test_game_slug_auto_generation_and_lookup(test_db):
    with test_db() as session:
        game = service.get_or_create_game(session, "Honkai: Star Rail")
        session.commit()
        assert game.slug == "honkai-star-rail"

        # Lookup by exact slug
        found_by_slug = service.get_game_by_name_or_slug(session, "honkai-star-rail")
        assert found_by_slug is not None
        assert found_by_slug.id == game.id

        # Lookup by exact name
        found_by_name = service.get_game_by_name_or_slug(session, "Honkai: Star Rail")
        assert found_by_name is not None
        assert found_by_name.id == game.id


def test_get_banners_unified_service_filters_and_pagination(test_db):
    b1 = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Mualani", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 21, 0, 0, 0, tzinfo=timezone.utc),
        phase=1,
    )
    b2 = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_WEAPON,
        limited_rewards=[Reward(name="Surf's Up", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 21, 0, 0, 0, tzinfo=timezone.utc),
        phase=1,
    )
    b3 = Banner(
        version="5.1",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Xilonen", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 2, 21, 0, 0, 0, tzinfo=timezone.utc),
        phase=1,
    )
    service.save_banners_to_db([b1, b2, b3], "Genshin Impact")

    # 1. Query by slug
    banners, total = service.get_banners("genshin-impact")
    assert total == 3
    assert len(banners) == 3

    # 2. Filter by banner type LIMITED_WEAPON
    weapons, total_w = service.get_banners("genshin-impact", banner_type=BannerType.LIMITED_WEAPON)
    assert total_w == 1
    assert weapons[0].limited_rewards[0].name == "Surf's Up"

    # 3. Filter by version "5.1"
    v51, total_v = service.get_banners("genshin-impact", version="5.1")
    assert total_v == 1
    assert v51[0].limited_rewards[0].name == "Xilonen"

    # 4. Pagination (page_size = 2)
    p1, total_p1 = service.get_banners("genshin-impact", page=1, page_size=2)
    assert total_p1 == 3
    assert len(p1) == 2

    p2, total_p2 = service.get_banners("genshin-impact", page=2, page_size=2)
    assert total_p2 == 3
    assert len(p2) == 1


def test_item_deduplication_and_relationship(test_db):
    """
    Test that running multiple banners featuring the same character (reruns)
    links to a SINGLE Item row, avoiding duplication.
    """
    b1 = Banner(
        version="1.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(
            name="Seele",
            rarity=5,
            is_featured=True,
            extra_data={"element": "Quantum", "path": "The Hunt", "local_wish": "/static/seele.png"},
        )],
        low_rate_rewards=[Reward(name="Natasha", rarity=4, is_featured=False)],
        start_date=datetime(2023, 4, 26, tzinfo=timezone.utc),
        end_date=datetime(2023, 5, 17, tzinfo=timezone.utc),
        phase=1,
    )
    b2 = Banner(
        version="1.4",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(
            name="Seele",
            rarity=5,
            is_featured=True,
            extra_data={"element": "Quantum", "path": "The Hunt", "local_wish": "/static/seele_v2.png"},
        )],
        low_rate_rewards=[Reward(name="Guinaifen", rarity=4, is_featured=False)],
        start_date=datetime(2023, 10, 27, tzinfo=timezone.utc),
        end_date=datetime(2023, 11, 14, tzinfo=timezone.utc),
        phase=2,
    )

    service.save_banners_to_db([b1, b2], "Honkai: Star Rail")

    # Verify only 1 Item row for Seele exists
    items = service.get_game_items("Honkai: Star Rail")
    seele_items = [i for i in items if i.name == "Seele"]
    assert len(seele_items) == 1

    seele = seele_items[0]
    assert seele.slug == "seele"
    assert seele.rarity == 5
    assert seele.item_type == "CHARACTER"
    assert seele.extra_data.get("element") == "Quantum"
    assert seele.extra_data.get("path") == "The Hunt"

    # Verify Seele is linked to both banners via rewards
    history = service.get_character_banner_history("Honkai: Star Rail", "Seele")
    assert len(history) == 2
    assert history[0].version == "1.4"
    assert history[1].version == "1.0"
    assert history[0].rewards[0].item_id == seele.id
    assert history[1].rewards[0].item_id == seele.id


def test_game_agnostic_extra_data_and_filtering(test_db):
    """
    Test that Item extra_data supports diverse non-standard gacha games
    (e.g., Uma Musume support cards, FGO craft essences, ZZZ bangboos).
    """
    with test_db() as session:
        game = service.get_or_create_game(session, "Uma Musume")
        session.commit()

        # Add a Trainee Character
        service.get_or_create_item(
            session=session,
            game_id=game.id,
            name="Special Week",
            rarity=3,
            item_type="CHARACTER",
            extra_data={"surface": "Turf", "distance": "Medium", "strategy": "Pace"},
        )

        # Add a Support Card (not a weapon!)
        service.get_or_create_item(
            session=session,
            game_id=game.id,
            name="Fine Motion (Support)",
            rarity=3,
            item_type="SUPPORT_CARD",
            extra_data={"card_type": "Wit", "training_effect": "15%"},
        )
        session.commit()

    all_items = service.get_game_items("Uma Musume")
    assert len(all_items) == 2

    trainees = service.get_game_items("Uma Musume", item_type="CHARACTER")
    assert len(trainees) == 1
    assert trainees[0].name == "Special Week"
    assert trainees[0].extra_data["surface"] == "Turf"

    cards = service.get_game_items("Uma Musume", item_type="SUPPORT_CARD")
    assert len(cards) == 1
    assert cards[0].name == "Fine Motion (Support)"
    assert cards[0].extra_data["card_type"] == "Wit"


def test_multi_featured_five_star_banner_deduplication_and_order_invariance(test_db):
    """
    Test that weapon banners with 2 featured 5★ weapons (e.g. Epitome Invocation)
    deduplicate cleanly even if the rewards are scraped in reverse order on subsequent runs.
    """
    # 1. Initial scrape: Weapon A first, Weapon B second
    w_banner_v1 = Banner(
        version="4.6",
        banner_type=BannerType.LIMITED_WEAPON,
        limited_rewards=[
            Reward(name="Crimson Moon's Semblance", rarity=5, is_featured=True),
            Reward(name="The First Great Magic", rarity=5, is_featured=True),
        ],
        low_rate_rewards=[
            Reward(name="Favonius Sword", rarity=4, is_featured=False),
        ],
        start_date=datetime(2024, 4, 24, 6, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 14, 17, 59, 59, tzinfo=timezone.utc),
        phase=1,
    )
    service.save_banners_to_db([w_banner_v1], "Genshin Impact")

    banners, total = service.get_banners("Genshin Impact", banner_type=BannerType.LIMITED_WEAPON)
    assert total == 1
    assert len(banners[0].limited_rewards) == 2

    # 2. Subsequent scrape: Weapon B listed first, Weapon A second, with additional rate up info
    w_banner_v2 = Banner(
        version="4.6",
        banner_type=BannerType.LIMITED_WEAPON,
        limited_rewards=[
            Reward(name="The First Great Magic", rarity=5, is_featured=True, extra_data={"type": "Bow"}),
            Reward(name="Crimson Moon's Semblance", rarity=5, is_featured=True, extra_data={"type": "Polearm"}),
        ],
        low_rate_rewards=[
            Reward(name="Favonius Sword", rarity=4, is_featured=False),
            Reward(name="The Bell", rarity=4, is_featured=False),
        ],
        start_date=datetime(2024, 4, 24, 6, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 14, 17, 59, 59, tzinfo=timezone.utc),
        phase=1,
    )
    service.save_banners_to_db([w_banner_v2], "Genshin Impact")

    # Verify that NO duplicate banner was created
    banners_after, total_after = service.get_banners("Genshin Impact", banner_type=BannerType.LIMITED_WEAPON)
    assert total_after == 1
    assert len(banners_after) == 1

    saved_banner = banners_after[0]
    assert len(saved_banner.limited_rewards) == 2
    assert len(saved_banner.low_rate_rewards) == 2

    # Verify both weapons are properly registered in Item table as WEAPON
    weapons = service.get_game_items("Genshin Impact", item_type="WEAPON")
    weapon_names = [w.name for w in weapons]
    assert "Crimson Moon's Semblance" in weapon_names
    assert "The First Great Magic" in weapon_names
    assert "Favonius Sword" in weapon_names
    assert "The Bell" in weapon_names


def test_chronicled_multi_character_banner_deduplication(test_db):
    """
    Test that Chronicled Wish banners with 3+ featured 5★ characters deduplicate properly.
    """
    c_banner_1 = Banner(
        version="4.5",
        banner_type=BannerType.CHRONICLED,
        limited_rewards=[
            Reward(name="Diluc", rarity=5, is_featured=True),
            Reward(name="Jean", rarity=5, is_featured=True),
            Reward(name="Mona", rarity=5, is_featured=True),
            Reward(name="Klee", rarity=5, is_featured=True),
            Reward(name="Albedo", rarity=5, is_featured=True),
            Reward(name="Eula", rarity=5, is_featured=True),
        ],
        low_rate_rewards=[],
        start_date=datetime(2024, 3, 13, 6, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2024, 4, 2, 17, 59, 59, tzinfo=timezone.utc),
        phase=1,
    )
    service.save_banners_to_db([c_banner_1], "Genshin Impact")

    banners, total = service.get_banners("Genshin Impact", banner_type=BannerType.CHRONICLED)
    assert total == 1
    assert len(banners[0].limited_rewards) == 6

    # Re-saving with enriched metadata
    c_banner_2 = Banner(
        version="4.5",
        banner_type=BannerType.CHRONICLED,
        limited_rewards=[
            Reward(name="Eula", rarity=5, is_featured=True, extra_data={"element": "Cryo"}),
            Reward(name="Albedo", rarity=5, is_featured=True, extra_data={"element": "Geo"}),
            Reward(name="Klee", rarity=5, is_featured=True, extra_data={"element": "Pyro"}),
            Reward(name="Mona", rarity=5, is_featured=True, extra_data={"element": "Hydro"}),
            Reward(name="Jean", rarity=5, is_featured=True, extra_data={"element": "Anemo"}),
            Reward(name="Diluc", rarity=5, is_featured=True, extra_data={"element": "Pyro"}),
        ],
        low_rate_rewards=[],
        start_date=datetime(2024, 3, 13, 6, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2024, 4, 2, 17, 59, 59, tzinfo=timezone.utc),
        phase=1,
    )
    service.save_banners_to_db([c_banner_2], "Genshin Impact")

    banners_after, total_after = service.get_banners("Genshin Impact", banner_type=BannerType.CHRONICLED)
    assert total_after == 1
    assert len(banners_after[0].limited_rewards) == 6




