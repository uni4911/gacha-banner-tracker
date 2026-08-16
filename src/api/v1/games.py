from __future__ import annotations
from fastapi import APIRouter
from src.schemas.schemas import GameResponse
from src.db.service import get_all_games

game_router = APIRouter(prefix="/games", tags=["Games"])


@game_router.get("", response_model=list[GameResponse], summary="Get all available games")
def list_games() -> list[GameResponse]:
    """Retrieve all games stored in the database."""
    games = get_all_games()
    return [GameResponse(id=g.id, name=g.name) for g in games]
