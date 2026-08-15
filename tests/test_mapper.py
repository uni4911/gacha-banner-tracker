from datetime import datetime, timezone
import pytest
from src.models.models import Banner, BannerType, Reward, Game
from src.db.models import BannerModel, RewardModel, GameModel
from src.db.mapper import (
    BannerMapper,
    RewardMapper,
    GameMapper,
    banner_to_model,
    model_to_banner,
    reward_to_model,
    model_to_reward,
    game_to_model,
    model_to_game,
)


def test_reward_to_model():
    reward = Reward(
        name="Raiden Shogun",
        rarity=5,
        is_featured=True,
        extra_data={"element": "Electro", "weapon": "Polearm"},
    )

    model = RewardMapper.to_model(reward, banner_id=10)

    assert isinstance(model, RewardModel)
    assert model.name == "Raiden Shogun"
    assert model.rarity == 5
    assert model.is_featured is True
    assert model.extra_data == {"element": "Electro", "weapon": "Polearm"}
    assert model.banner_id == 10


def test_model_to_reward():
    model = RewardModel(
        id=1,
        banner_id=10,
        name="Kujou Sara",
        rarity=4,
        is_featured=False,
        extra_data={"element": "Electro"},
    )

    reward = RewardMapper.to_domain(model)

    assert isinstance(reward, Reward)
    assert reward.name == "Kujou Sara"
    assert reward.rarity == 4
    assert reward.is_featured is False
    assert reward.extra_data == {"element": "Electro"}


def test_banner_to_model():
    limited_reward = Reward(name="Mualani", rarity=5, is_featured=True)
    low_rate_reward_1 = Reward(name="Kachina", rarity=4, is_featured=False)
    low_rate_reward_2 = Reward(name="Bennett", rarity=4, is_featured=False)

    start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 21, 18, 0, 0, tzinfo=timezone.utc)

    banner = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[limited_reward],
        low_rate_rewards=[low_rate_reward_1, low_rate_reward_2],
        start_date=start,
        end_date=end,
        phase=1,
    )

    model = BannerMapper.to_model(banner, game_id=1)

    assert isinstance(model, BannerModel)
    assert model.version == "5.0"
    assert model.phase == 1
    assert model.banner_type == "LIMITED_CHARACTER"
    assert model.start_date == start
    assert model.end_date == end
    assert model.game_id == 1
    assert len(model.rewards) == 3
    assert model.rewards[0].name == "Mualani"
    assert model.rewards[0].is_featured is True
    assert model.rewards[1].name == "Kachina"
    assert model.rewards[1].is_featured is False
    assert model.rewards[2].name == "Bennett"
    assert model.rewards[2].is_featured is False


def test_model_to_banner():
    start = datetime(2026, 1, 1, 10, 0, 0)
    end = datetime(2026, 1, 21, 18, 0, 0)

    model = BannerModel(
        id=100,
        game_id=1,
        version="5.0",
        phase=1,
        banner_type="LIMITED_CHARACTER",
        start_date=start,
        end_date=end,
        rewards=[
            RewardModel(name="Mualani", rarity=5, is_featured=True, extra_data={}),
            RewardModel(name="Kachina", rarity=4, is_featured=False, extra_data={}),
            RewardModel(name="Bennett", rarity=4, is_featured=False, extra_data={}),
        ],
    )

    banner = BannerMapper.to_domain(model)

    assert isinstance(banner, Banner)
    assert banner.version == "5.0"
    assert banner.phase == 1
    assert banner.banner_type == BannerType.LIMITED_CHARACTER
    assert banner.start_date == start.replace(tzinfo=timezone.utc)
    assert banner.end_date == end.replace(tzinfo=timezone.utc)
    assert len(banner.limited_rewards) == 1
    assert banner.limited_rewards[0].name == "Mualani"
    assert len(banner.low_rate_rewards) == 2
    assert [r.name for r in banner.low_rate_rewards] == ["Kachina", "Bennett"]


def test_standalone_function_aliases():
    reward = Reward(name="Test", rarity=5, is_featured=True)
    rmodel = reward_to_model(reward)
    assert rmodel.name == "Test"
    r_domain = model_to_reward(rmodel)
    assert r_domain.name == "Test"

    banner = Banner(
        version="1.0",
        banner_type=BannerType.STANDARD_CHARACTER,
        limited_rewards=[],
        low_rate_rewards=[],
        start_date=datetime(2026, 1, 1),
        end_date=None,
        phase=1,
    )
    bmodel = banner_to_model(banner)
    assert bmodel.banner_type == "STANDARD_CHARACTER"
    b_domain = model_to_banner(bmodel)
    assert b_domain.banner_type == BannerType.STANDARD_CHARACTER
    assert b_domain.end_date is None

    game = Game(name="Genshin Impact", banners=[banner])
    gmodel = game_to_model(game)
    assert gmodel.name == "Genshin Impact"
    assert len(gmodel.banners) == 1
    g_domain = model_to_game(gmodel)
    assert g_domain.name == "Genshin Impact"
    assert len(g_domain.banners) == 1


def test_game_mapper():
    banner = Banner(
        version="5.0",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Mualani", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=None,
        phase=1,
    )
    game = Game(name="Genshin Impact", banners=[banner])

    # Game to Model
    game_model = GameMapper.to_model(game)
    assert isinstance(game_model, GameModel)
    assert game_model.name == "Genshin Impact"
    assert len(game_model.banners) == 1

    # Model to Game
    domain_game = GameMapper.to_domain(game_model)
    assert isinstance(domain_game, Game)
    assert domain_game.name == "Genshin Impact"
    assert len(domain_game.banners) == 1
    assert domain_game.banners[0].version == "5.0"

