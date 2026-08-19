from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from src.models.models import BannerType
from src.db.models import GameModel, BannerModel, RewardModel
from src.schemas.schemas import (
    RewardBase,
    RewardCreate,
    RewardUpdate,
    RewardResponse,
    BannerBase,
    BannerCreate,
    BannerUpdate,
    BannerResponse,
    GameBase,
    GameCreate,
    GameUpdate,
    GameResponse,
    GameDetailResponse,
    GameWithBannersResponse,
)


def test_reward_schemas():
    # RewardBase & RewardCreate
    r_create = RewardCreate(name="Raiden Shogun", rarity=5, is_featured=True, extra_data={"weapon": "Polearm"})
    assert r_create.name == "Raiden Shogun"
    assert r_create.rarity == 5
    assert r_create.is_featured is True
    assert r_create.extra_data == {"weapon": "Polearm"}

    # Default extra_data
    r_default = RewardCreate(name="Bennett", rarity=4, is_featured=False)
    assert r_default.extra_data == {}

    # RewardResponse from dict
    r_resp = RewardResponse(id=1, banner_id=10, name="Bennett", rarity=4, is_featured=False)
    assert r_resp.id == 1
    assert r_resp.banner_id == 10

    # RewardResponse from ORM model
    r_model = RewardModel(id=2, banner_id=20, name="Kachina", rarity=4, is_featured=False, extra_data={"element": "Geo"})
    r_resp_orm = RewardResponse.model_validate(r_model)
    assert r_resp_orm.id == 2
    assert r_resp_orm.banner_id == 20
    assert r_resp_orm.name == "Kachina"
    assert r_resp_orm.extra_data == {"element": "Geo"}


def test_banner_schemas_base_and_create():
    start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 21, 18, 0, 0, tzinfo=timezone.utc)

    # BannerCreate with enum
    b_create = BannerCreate(
        version="5.0",
        phase=1,
        banner_type=BannerType.LIMITED_CHARACTER,
        start_date=start,
        end_date=end,
        rewards=[
            RewardCreate(name="Mualani", rarity=5, is_featured=True),
            RewardCreate(name="Kachina", rarity=4, is_featured=False),
        ],
    )
    assert b_create.version == "5.0"
    assert b_create.phase == 1
    assert b_create.banner_type == BannerType.LIMITED_CHARACTER
    assert len(b_create.rewards) == 2

    # BannerCreate with string banner_type
    b_create_str = BannerCreate(
        version="5.0",
        phase=1,
        banner_type="LIMITED_CHARACTER",
        start_date=start,
    )
    assert b_create_str.banner_type == BannerType.LIMITED_CHARACTER
    assert b_create_str.end_date is None


def test_banner_response_orm_validation():
    start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 21, 18, 0, 0, tzinfo=timezone.utc)

    b_model = BannerModel(
        id=5,
        game_id=1,
        version="5.0",
        phase=1,
        banner_type="LIMITED_CHARACTER",
        start_date=start,
        end_date=end,
        rewards=[
            RewardModel(id=10, banner_id=5, name="Mualani", rarity=5, is_featured=True, extra_data={}),
            RewardModel(id=11, banner_id=5, name="Kachina", rarity=4, is_featured=False, extra_data={}),
        ],
    )

    b_resp = BannerResponse.model_validate(b_model)
    assert b_resp.id == 5
    assert b_resp.game_id == 1
    assert b_resp.version == "5.0"
    assert b_resp.phase == 1
    assert b_resp.banner_type == BannerType.LIMITED_CHARACTER
    assert len(b_resp.rewards) == 2
    assert b_resp.rewards[0].name == "Mualani"
    assert b_resp.rewards[0].id == 10

    # JSON serialization
    json_data = b_resp.model_dump(mode="json")
    assert json_data["banner_type"] == "LIMITED_CHARACTER"
    assert json_data["id"] == 5


def test_banner_update_schema():
    b_update = BannerUpdate(version="5.1", phase=2, banner_type="LIMITED_WEAPON")
    assert b_update.version == "5.1"
    assert b_update.phase == 2
    assert b_update.banner_type == BannerType.LIMITED_WEAPON
    assert b_update.start_date is None


def test_game_schemas():
    # GameCreate
    g_create = GameCreate(name="Genshin Impact")
    assert g_create.name == "Genshin Impact"

    # GameUpdate
    g_update = GameUpdate(name="Honkai: Star Rail")
    assert g_update.name == "Honkai: Star Rail"

    # GameResponse from ORM
    g_model = GameModel(id=1, name="Genshin Impact")
    g_resp = GameResponse.model_validate(g_model)
    assert g_resp.id == 1
    assert g_resp.name == "Genshin Impact"
    assert g_resp.slug == "genshin-impact"

    # GameDetailResponse with banners
    start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    b_model = BannerModel(
        id=10,
        game_id=1,
        version="5.0",
        phase=1,
        banner_type="LIMITED_CHARACTER",
        start_date=start,
        end_date=None,
        rewards=[],
    )
    g_model.banners = [b_model]

    g_detail = GameDetailResponse.model_validate(g_model)
    assert g_detail.id == 1
    assert len(g_detail.banners) == 1
    assert g_detail.banners[0].id == 10
    assert g_detail.banners[0].version == "5.0"

    # Verify alias
    assert GameWithBannersResponse is GameDetailResponse


def test_paginated_banner_response():
    from src.schemas.schemas import PaginatedBannerResponse
    start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    b_resp = BannerResponse(
        id=1,
        version="5.0",
        phase=1,
        banner_type=BannerType.LIMITED_CHARACTER,
        start_date=start,
    )
    paginated = PaginatedBannerResponse(
        items=[b_resp],
        total=1,
        page=1,
        page_size=20,
        total_pages=1,
    )
    assert paginated.total == 1
    assert paginated.page == 1
    assert len(paginated.items) == 1
    assert paginated.items[0].version == "5.0"

