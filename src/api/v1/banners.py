from __future__ import annotations
from datetime import datetime, timezone
from typing import Annotated, Any
from fastapi import APIRouter, Path, Query, status

from src.schemas.schemas import BannerCreate, BannerResponse
from src.models.models import Banner, Reward, Server
from src.db.service import (
    get_active_banners,
    get_upcoming_banners,
    get_character_banner_history,
    get_banners_by_version,
    save_banners_to_db,
)

banner_router = APIRouter(prefix="/games/{game_name}/banners", tags=["Banners"])


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
) -> list[BannerResponse]:
    """Retrieve all currently active banners for a specific game."""
    target_time = current_time if current_time is not None else datetime.now(timezone.utc)
    return get_active_banners(game_name, target_time, server=server)


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
) -> list[BannerResponse]:
    """Retrieve all upcoming banners starting after current_time for a specific game."""
    target_time = current_time if current_time is not None else datetime.now(timezone.utc)
    return get_upcoming_banners(game_name, target_time, server=server)


@banner_router.get(
    "/character/{character_name}",
    response_model=list[BannerResponse],
    summary="Get character banner history",
)
def get_character_history(
    game_name: Annotated[str, Path(description="Name of the game (e.g. Genshin Impact)")],
    character_name: Annotated[str, Path(description="Name of the character (e.g. Raiden Shogun)")],
) -> list[BannerResponse]:
    """Retrieve all past and active banners featuring a specific character."""
    return get_character_banner_history(game_name, character_name)


@banner_router.get(
    "/version/{version}",
    response_model=list[BannerResponse],
    summary="Get banners by game version",
)
def get_by_version(
    game_name: Annotated[str, Path(description="Name of the game (e.g. Genshin Impact)")],
    version: Annotated[str, Path(description="Game patch/version (e.g. 5.0)")],
) -> list[BannerResponse]:
    """Retrieve all banners for a specific game version/patch."""
    return get_banners_by_version(game_name, version)


@banner_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Save banners to database",
)
def create_banners(
    game_name: Annotated[str, Path(description="Name of the game to save banners for")],
    banners: list[BannerCreate],
) -> dict[str, Any]:
    """Save a list of banners and rewards to the database for a given game."""
    domain_banners: list[Banner] = []
    for b in banners:
        if b.limited_rewards or b.low_rate_rewards:
            limited = [
                Reward(
                    name=r.name,
                    rarity=r.rarity,
                    is_featured=r.is_featured,
                    extra_data=r.extra_data,
                )
                for r in b.limited_rewards
            ]
            low_rate = [
                Reward(
                    name=r.name,
                    rarity=r.rarity,
                    is_featured=r.is_featured,
                    extra_data=r.extra_data,
                )
                for r in b.low_rate_rewards
            ]
        else:
            limited = [
                Reward(
                    name=r.name,
                    rarity=r.rarity,
                    is_featured=r.is_featured,
                    extra_data=r.extra_data,
                )
                for r in b.rewards
                if r.is_featured
            ]
            low_rate = [
                Reward(
                    name=r.name,
                    rarity=r.rarity,
                    is_featured=r.is_featured,
                    extra_data=r.extra_data,
                )
                for r in b.rewards
                if not r.is_featured
            ]

        domain_banners.append(
            Banner(
                version=b.version,
                banner_type=b.banner_type,
                limited_rewards=limited,
                low_rate_rewards=low_rate,
                start_date=b.start_date,
                end_date=b.end_date,
                phase=b.phase,
            )
        )

    save_banners_to_db(domain_banners, game_name)
    return {
        "message": f"Successfully processed and saved {len(domain_banners)} banner(s) for '{game_name}'.",
        "count": len(domain_banners),
    }