from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.schemas.schemas import GameResponse, ItemResponse
from src.db.service import get_all_games, get_game, get_game_items
from fastapi import Query

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


@game_router.get(
    "/{identifier}/items",
    response_model=list[ItemResponse],
    summary="Get all items (characters, weapons, cards, etc.) for a game",
)
def list_game_items(
    identifier: Annotated[str, Path(description="Game slug or name")],
    item_type: Annotated[str | None, Query(description="Filter by item type (CHARACTER, WEAPON, SUPPORT_CARD, etc.)")] = None,
    rarity: Annotated[int | None, Query(description="Filter by rarity (e.g. 4, 5)")] = None,
    db: Session = Depends(get_db),
) -> list[ItemResponse]:
    """Retrieve all unique characters, weapons, or cards registered for a game."""
    game = get_game(identifier, db=db)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game '{identifier}' not found.",
        )
    items = get_game_items(game_identifier=identifier, item_type=item_type, rarity=rarity, db=db)
    return items


@game_router.get(
    "/{identifier}/characters",
    response_model=list[ItemResponse],
    summary="Get all characters for a game",
)
def list_game_characters(
    identifier: Annotated[str, Path(description="Game slug or name")],
    rarity: Annotated[int | None, Query(description="Filter by rarity (e.g. 4, 5)")] = None,
    db: Session = Depends(get_db),
) -> list[ItemResponse]:
    """Retrieve all distinct characters registered for a game."""
    return list_game_items(identifier=identifier, item_type="CHARACTER", rarity=rarity, db=db)


@game_router.get(
    "/{identifier}/weapons",
    response_model=list[ItemResponse],
    summary="Get all weapons/light cones/equipment for a game",
)
def list_game_weapons(
    identifier: Annotated[str, Path(description="Game slug or name")],
    rarity: Annotated[int | None, Query(description="Filter by rarity (e.g. 4, 5)")] = None,
    db: Session = Depends(get_db),
) -> list[ItemResponse]:
    """Retrieve all distinct weapons or equipment registered for a game."""
    return list_game_items(identifier=identifier, item_type="WEAPON", rarity=rarity, db=db)
