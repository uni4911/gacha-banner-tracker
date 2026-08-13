from src.db.models import GameModel, RewardModel, BannerModel
from src.db.database import SessionLocal
from src.models.models import Banner
from sqlalchemy.orm import Session
from sqlalchemy import exists, select


def get_or_create_game(session: Session, game_name : str) -> GameModel:
    game = session.query(GameModel).filter_by(name=game_name).first()
    if not game:
        game = GameModel(name=game_name)
        session.add(game)
        session.flush()
    return game


def save_banners_to_db(banners: list[Banner], game_name: str) -> None:
    with SessionLocal() as db:
        game = get_or_create_game(db, game_name)
        for banner_data in banners:
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
                banner_type = banner_data.banner_type.name
                banner_model = BannerModel(game_id = game.id, version = banner_data.version, phase = banner_data.phase, 
                                        banner_type = banner_type, start_date = banner_data.start_date, end_date = banner_data.end_date)     
                
                for reward in banner_data.limited_rewards:
                    reward_model = RewardModel(name=reward.name, rarity=reward.rarity, is_featured = reward.is_featured, extra_data = reward.extra_data)
                    banner_model.rewards.append(reward_model)
                for reward in banner_data.low_rate_rewards:
                    reward_model = RewardModel(name=reward.name, rarity=reward.rarity, is_featured = reward.is_featured, extra_data = reward.extra_data)
                    banner_model.rewards.append(reward_model)

                db.add(banner_model)
        db.commit()

