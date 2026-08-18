from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from src.db.models import BannerType


# ============================================================================
# Reward Schemas
# ============================================================================

class RewardBase(BaseModel):
    name: str
    rarity: int
    is_featured: bool
    extra_data: dict[str, Any] = Field(default_factory=dict)


class RewardCreate(RewardBase):
    pass


class RewardUpdate(BaseModel):
    name: str | None = None
    rarity: int | None = None
    is_featured: bool | None = None
    extra_data: dict[str, Any] | None = None


class RewardResponse(RewardBase):
    id: int | None = None
    banner_id: int | None = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Banner Schemas
# ============================================================================

class BannerBase(BaseModel):
    version: str
    phase: int
    banner_type: BannerType
    start_date: datetime
    end_date: datetime | None = None

    @field_validator("banner_type", mode="before")
    @classmethod
    def parse_banner_type(cls, v: Any) -> BannerType:
        if isinstance(v, str):
            try:
                return BannerType[v]
            except KeyError:
                return BannerType[v.upper()]
        return v

    @field_serializer("banner_type", when_used="json")
    def serialize_banner_type(self, v: BannerType) -> str:
        return v.name if isinstance(v, BannerType) else str(v)


class BannerCreate(BannerBase):
    game_id: int | None = None
    rewards: list[RewardCreate] = Field(default_factory=list)
    limited_rewards: list[RewardCreate] = Field(default_factory=list)
    low_rate_rewards: list[RewardCreate] = Field(default_factory=list)


class BannerUpdate(BaseModel):
    version: str | None = None
    phase: int | None = None
    banner_type: BannerType | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    @field_validator("banner_type", mode="before")
    @classmethod
    def parse_banner_type(cls, v: Any) -> BannerType | None:
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return BannerType[v]
            except KeyError:
                return BannerType[v.upper()]
        return v

    @field_serializer("banner_type", when_used="json")
    def serialize_banner_type(self, v: BannerType | None) -> str | None:
        if v is None:
            return None
        return v.name if isinstance(v, BannerType) else str(v)


class BannerResponse(BannerBase):
    id: int | None = None
    game_id: int | None = None
    rewards: list[RewardResponse] = Field(default_factory=list)
    limited_rewards: list[RewardResponse] = Field(default_factory=list)
    low_rate_rewards: list[RewardResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Game Schemas
# ============================================================================

class GameBase(BaseModel):
    name: str


class GameCreate(GameBase):
    pass


class GameUpdate(BaseModel):
    name: str | None = None


class GameResponse(GameBase):
    id: int | None = None
    model_config = ConfigDict(from_attributes=True)


class GameDetailResponse(GameResponse):
    banners: list[BannerResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# Convenient alias
GameWithBannersResponse = GameDetailResponse


# ============================================================================
# Sync Schemas
# ============================================================================

class SyncTriggerRequest(BaseModel):
    game_names: list[str] | None = Field(
        default=None,
        description="Optional list of game names to scrape. If omitted, scrapes all configured games.",
    )
    download_images: bool | None = Field(
        default=None,
        description="Optional override for whether to download artwork/icons locally.",
    )


class SyncStatusResponse(BaseModel):
    is_running: bool
    status: str
    last_synced_at: datetime | None = None
    next_run_time: datetime | None = None
    last_duration_seconds: float | None = None
    last_error: str | None = None
    last_results: dict[str, int] | None = None
    scheduler_active: bool = False


class SyncTriggerResponse(BaseModel):
    status: str
    message: str
    is_running: bool
    last_synced_at: str | None = None
    duration_seconds: float | None = None
    results: dict[str, int] | None = None
    error: str | None = None
