from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.schemas.schemas import GameResponse
from src.db.service import get_all_games, get_game

game_router = APIRouter(prefix="/games", tags=["Games"])


@game_router.get("", response_model=list[GameResponse], summary="Get all available games")
def list_games(db: Session = Depends(get_db)) -> list[GameResponse]:
    """Retrieve all games stored in the database."""
    games = get_all_games(db=db)
    return [GameResponse(id=g.id, name=g.name, slug=g.slug) for g in games]


@game_router.get("/{identifier}", response_model=GameResponse, summary="Get game details by slug or name")
def get_game_detail(
    identifier: Annotated[str, Path(description="Game slug (e.g. 'genshin-impact') or full name")],
    db: Session = Depends(get_db),
) -> GameResponse:
    """Retrieve details of a single game by its slug or name."""
    game = get_game(identifier, db=db)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game '{identifier}' not found.",
        )
    return GameResponse(id=game.id, name=game.name, slug=game.slug)
