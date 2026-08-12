from src.db.models import GameModel, RewardModel
from database import SessionLocal
from sqlalchemy.orm import Session
from src.models.models import Banner

def get_or_create_game(session: Session, game_name : str) -> GameModel:
    game = session.query(GameModel).filter_by(name=game_name).first()
    if not game:
        game = GameModel(name=game_name)
        session.add(game)
        session.flush()
    return game


def save_banners_to_db(banners: list[Banner]) -> None:
   pass