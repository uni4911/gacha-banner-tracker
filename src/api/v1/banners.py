from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from src.schemas.schemas import BannerCreate, BannerResponse, PaginatedBannerResponse
from src.db.models import Banner, Reward, Server, BannerType
from src.db.database import get_db
from src.db.service import (
    get_banners,
    get_active_banners,
    get_upcoming_banners,
    get_character_banner_history,
    get_banners_by_version,
    save_banners_to_db,
)

banner_router = APIRouter(prefix="/games/{game_name}/banners", tags=["Banners"])


@banner_router.get(
    "",
    response_model=PaginatedBannerResponse,
    summary="List banners with filters and pagination",
)
def list_banners(
    game_name: Annotated[str, Path(description="Game name or slug (e.g. 'genshin-impact' or 'Genshin Impact')")],
    version: Annotated[str | None, Query(description="Filter by game version (e.g. '5.0')")] = None,
    phase: Annotated[int | None, Query(description="Filter by banner phase (1 or 2)")] = None,
    banner_type: Annotated[BannerType | None, Query(description="Filter by banner type")] = None,
    character: Annotated[str | None, Query(description="Filter by character or weapon name")] = None,
    status_filter: Annotated[
        Literal["all", "active", "upcoming", "ended"],
        Query(alias="status", description="Filter by banner status (all, active, upcoming, ended)"),
    ] = "all",
    server: Annotated[Server | None, Query(description="Optional server region (ASIA, EUROPE, AMERICA)")] = None,
    current_time: Annotated[
        datetime | None,
        Query(description="Reference datetime for active/upcoming filtering (defaults to UTC now)"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (starts at 1)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of items per page")] = 20,
    db: Session = Depends(get_db),
) -> PaginatedBannerResponse:
    """
    Retrieve banners for a game with optional filtering by version, phase, banner type, character,
    and lifecycle status (active, upcoming, ended), supporting server timezone offsets and pagination.
    """
    banners, total = get_banners(
        game_identifier=game_name,
        version=version,
        phase=phase,
        banner_type=banner_type,
        character_name=character,
        status=status_filter,
        server=server,
        current_time=current_time,
        page=page,
        page_size=page_size,
        db=db,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedBannerResponse(
        items=banners,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@banner_router.get("/active", response_model=list[BannerResponse], summary="Get active banners")
def get_active(
    game_name: Annotated[str, Path(description="Name of the game (e.g. Genshin Impact)")],
    current_time: Annotated[
        datetime | None,
        Query(description="Current datetime to query active banners for (defaults to UTC now)"),
    ] = None,
    server: Annotated[
        Server | None,
        Query(description="Optional server region (ASIA, EUROPE, AMERICA)"),
    ] = None,
    db: Session = Depends(get_db),
) -> list[Banner]:
    """Retrieve all currently active banners for a specific game."""
    target_time = current_time if current_time is not None else datetime.now(timezone.utc)
    return get_active_banners(game_name, target_time, server=server, db=db)


@banner_router.get("/upcoming", response_model=list[BannerResponse], summary="Get upcoming banners")
def get_upcoming(
    game_name: Annotated[str, Path(description="Name of the game (e.g. Genshin Impact)")],
    current_time: Annotated[
        datetime | None,
        Query(description="Current datetime to query upcoming banners for (defaults to UTC now)"),
    ] = None,
    server: Annotated[
        Server | None,
        Query(description="Optional server region (ASIA, EUROPE, AMERICA)"),
    ] = None,
    db: Session = Depends(get_db),
) -> list[Banner]:
    """Retrieve all upcoming banners starting after current_time for a specific game."""
    target_time = current_time if current_time is not None else datetime.now(timezone.utc)
    return get_upcoming_banners(game_name, target_time, server=server, db=db)


@banner_router.get(
    "/character/{character_name}",
    response_model=list[BannerResponse],
    summary="Get character banner history",
)
def get_character_history(
    game_name: Annotated[str, Path(description="Name of the game (e.g. Genshin Impact)")],
    character_name: Annotated[str, Path(description="Name of the character (e.g. Raiden Shogun)")],
    db: Session = Depends(get_db),
) -> list[Banner]:
    """Retrieve all past and active banners featuring a specific character."""
    return get_character_banner_history(game_name, character_name, db=db)


@banner_router.get(
    "/version/{version}",
    response_model=list[BannerResponse],
    summary="Get banners by game version",
)
def get_by_version(
    game_name: Annotated[str, Path(description="Name of the game (e.g. Genshin Impact)")],
    version: Annotated[str, Path(description="Game patch/version (e.g. 5.0)")],
    db: Session = Depends(get_db),
) -> list[Banner]:
    """Retrieve all banners for a specific game version/patch."""
    return get_banners_by_version(game_name, version, db=db)


@banner_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Save banners to database",
)
def create_banners(
    game_name: Annotated[str, Path(description="Name of the game to save banners for")],
    banners: list[BannerCreate],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Save a list of banners and rewards to the database for a given game."""
    db_banners: list[Banner] = []
    for b in banners:
        rewards_list: list[Reward] = []
        if b.limited_rewards or b.low_rate_rewards:
            for r in b.limited_rewards:
                rewards_list.append(
                    Reward(name=r.name, rarity=r.rarity, is_featured=True, extra_data=r.extra_data)
                )
            for r in b.low_rate_rewards:
                rewards_list.append(
                    Reward(name=r.name, rarity=r.rarity, is_featured=False, extra_data=r.extra_data)
                )
        else:
            for r in b.rewards:
                rewards_list.append(
                    Reward(name=r.name, rarity=r.rarity, is_featured=r.is_featured, extra_data=r.extra_data)
                )

        db_banners.append(
            Banner(
                version=b.version,
                banner_type=b.banner_type,
                rewards=rewards_list,
                start_date=b.start_date,
                end_date=b.end_date,
                phase=b.phase,
            )
        )

    save_banners_to_db(db_banners, game_name, db=db)
    return {
        "message": f"Successfully processed and saved {len(db_banners)} banner(s) for '{game_name}'.",
        "count": len(db_banners),
    }