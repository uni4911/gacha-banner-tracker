from src.db.models import GameModel, RewardModel, BannerModel
from src.db.database import SessionLocal
from src.db.mapper import BannerMapper
from src.models.models import Banner, Server
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import exists, select, or_
from datetime import datetime


def get_or_create_game(session: Session, game_name: str) -> GameModel:
    game = session.scalar(select(GameModel).where(GameModel.name == game_name))
    if not game:
        game = GameModel(name=game_name)
        session.add(game)
        session.flush()
    return game


def save_banners_to_db(banners: list[Banner], game_name: str) -> None:
    with SessionLocal() as db:
        game = get_or_create_game(db, game_name)
        for banner_data in banners:
            if not banner_data.limited_rewards:
                continue

            stmt = (
                select(BannerModel.id)
                .join(BannerModel.rewards)
                .where(
                    BannerModel.game_id == game.id,
                    BannerModel.version == banner_data.version,
                    RewardModel.name == banner_data.limited_rewards[0].name,
                )
                .limit(1)
            )

            if not db.scalar(stmt):
                banner_model = BannerMapper.to_model(banner_data, game_id=game.id)
                db.add(banner_model)
        db.commit()


def get_active_banners(game_name: str, current_time: datetime, server: Server | None = None) -> list[Banner]:
    with SessionLocal() as db:
        stmt = (
            select(BannerModel)
            .join(GameModel)
            .where(
                GameModel.name == game_name,
                BannerModel.start_date <= current_time,
                or_(BannerModel.end_date >= current_time, BannerModel.end_date.is_(None)),
            )
        .options(selectinload(BannerModel.rewards))
        .order_by(BannerModel.start_date.desc())
        .distinct())
        banner_models = db.scalars(stmt).all()
        return [BannerMapper.to_domain(model) for model in banner_models]


def get_upcoming_banners(game_name: str, current_time: datetime, server: Server | None) -> list[Banner]:
    with SessionLocal() as db:
        stmt = (
            select(BannerModel)
            .join(GameModel)
            .where(
                GameModel.name == game_name,
                BannerModel.start_date > current_time
            ).options(selectinload(BannerModel.rewards))
            .order_by(BannerModel.start_date.desc())
            .distinct())
        banner_models = db.scalars(stmt).all()
        return [BannerMapper.to_domain(model) for model in banner_models]
    
def get_character_banner_history(game_name: str, character_name: str) -> list[Banner]:
    with SessionLocal() as db:
        stmt = (
            select(BannerModel)
            .join(BannerModel.game).join(BannerModel.rewards).
            where(
                GameModel.name == game_name,
                RewardModel.name == character_name
            )
        .options(selectinload(BannerModel.rewards))
        .order_by(BannerModel.start_date.desc())
        .distinct())
        banner_models = db.scalars(stmt).all()
        return [BannerMapper.to_domain(model) for model in banner_models]


def get_banners_by_version(game_name: str, version: str) -> list[Banner]:
    with SessionLocal() as db:
        stmt =(
            select(BannerModel)
            .join(BannerModel.game)
            .where(BannerModel.version == version)
        ).options(selectinload(BannerModel.rewards))

        banner_models = db.scalars(stmt).all()
        return [BannerModel.to_domain(model) for model in banner_models]
