"""
Compatibility mapping layer.
With unified SQLAlchemy models, models can be used directly without translation.
"""
from __future__ import annotations
from typing import Any
from src.db.models import Banner, Reward, Game, BannerType, BannerModel, RewardModel, GameModel


class RewardMapper:
    @staticmethod
    def to_model(reward: Reward, banner_id: int | None = None) -> Reward:
        if banner_id is not None:
            reward.banner_id = banner_id
        return reward

    @staticmethod
    def to_domain(model: Reward) -> Reward:
        return model


class BannerMapper:
    @staticmethod
    def to_model(banner: Banner, game_id: int | None = None) -> Banner:
        if game_id is not None:
            banner.game_id = game_id
        return banner

    @staticmethod
    def to_domain(model: Banner) -> Banner:
        return model


class GameMapper:
    @staticmethod
    def to_model(game: Game) -> Game:
        return game

    @staticmethod
    def to_domain(model: Game) -> Game:
        return model


reward_to_model = RewardMapper.to_model
model_to_reward = RewardMapper.to_domain
banner_to_model = BannerMapper.to_model
model_to_banner = BannerMapper.to_domain
game_to_model = GameMapper.to_model
model_to_game = GameMapper.to_domain
