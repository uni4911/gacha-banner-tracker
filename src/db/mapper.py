from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from src.models.models import Banner, Reward, BannerType, Game
from src.db.models import BannerModel, RewardModel, GameModel


class RewardMapper:
    """Mapper for converting between Reward (domain) and RewardModel (database)."""

    @staticmethod
    def to_model(reward: Reward, banner_id: int | None = None) -> RewardModel:
        """Converts a domain Reward to a database RewardModel."""
        kwargs: dict[str, Any] = {
            "name": reward.name,
            "rarity": reward.rarity,
            "is_featured": reward.is_featured,
            "extra_data": dict(reward.extra_data) if reward.extra_data else {},
        }
        if banner_id is not None:
            kwargs["banner_id"] = banner_id

        return RewardModel(**kwargs)

    @staticmethod
    def to_domain(model: RewardModel) -> Reward:
        """Converts a database RewardModel to a domain Reward."""
        return Reward(
            name=model.name,
            rarity=model.rarity,
            is_featured=model.is_featured,
            extra_data=dict(model.extra_data) if model.extra_data else {},
        )


class BannerMapper:
    """Mapper for converting between Banner (domain) and BannerModel (database)."""

    @staticmethod
    def to_model(banner: Banner, game_id: int | None = None) -> BannerModel:
        """Converts a domain Banner to a database BannerModel, including its rewards."""
        banner_type_str = (
            banner.banner_type.name
            if isinstance(banner.banner_type, BannerType)
            else str(banner.banner_type)
        )

        kwargs: dict[str, Any] = {
            "version": banner.version,
            "phase": banner.phase,
            "banner_type": banner_type_str,
            "start_date": banner.start_date,
            "end_date": banner.end_date,
        }
        if game_id is not None:
            kwargs["game_id"] = game_id

        banner_model = BannerModel(**kwargs)

        rewards: list[RewardModel] = []
        for reward in banner.limited_rewards:
            rewards.append(RewardMapper.to_model(reward))
        for reward in banner.low_rate_rewards:
            rewards.append(RewardMapper.to_model(reward))

        banner_model.rewards = rewards
        return banner_model

    @staticmethod
    def to_domain(model: BannerModel) -> Banner:
        """Converts a database BannerModel to a domain Banner."""
        if isinstance(model.banner_type, BannerType):
            banner_type = model.banner_type
        else:
            try:
                banner_type = BannerType[model.banner_type]
            except KeyError:
                banner_type = BannerType[model.banner_type.upper()]

        limited_rewards: list[Reward] = []
        low_rate_rewards: list[Reward] = []

        if model.rewards:
            for reward_model in model.rewards:
                domain_reward = RewardMapper.to_domain(reward_model)
                if domain_reward.is_featured:
                    limited_rewards.append(domain_reward)
                else:
                    low_rate_rewards.append(domain_reward)

        start_date = model.start_date
        if start_date is not None and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

        end_date = model.end_date
        if end_date is not None and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        return Banner(
            version=model.version,
            banner_type=banner_type,
            limited_rewards=limited_rewards,
            low_rate_rewards=low_rate_rewards,
            start_date=start_date,
            end_date=end_date,
            phase=model.phase,
        )


class GameMapper:
    """Mapper for converting between Game (domain) and GameModel (database)."""

    @staticmethod
    def to_model(game: Game) -> GameModel:
        """Converts a domain Game to a database GameModel."""
        game_model = GameModel(name=game.name)
        if game.banners:
            game_model.banners = [BannerMapper.to_model(b) for b in game.banners]
        return game_model

    @staticmethod
    def to_domain(model: GameModel) -> Game:
        """Converts a database GameModel to a domain Game."""
        banners = (
            [BannerMapper.to_domain(b) for b in model.banners]
            if model.banners
            else []
        )
        return Game(name=model.name, banners=banners)


# Convenience standalone functions
reward_to_model = RewardMapper.to_model
model_to_reward = RewardMapper.to_domain
banner_to_model = BannerMapper.to_model
model_to_banner = BannerMapper.to_domain
game_to_model = GameMapper.to_model
model_to_game = GameMapper.to_domain
