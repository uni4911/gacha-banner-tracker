from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from src.db.models import BannerType


# ============================================================================
# Item Schemas
# ============================================================================

class ItemBase(BaseModel):
    name: str
    slug: str | None = None
    item_type: str = "CHARACTER"
    rarity: int = 5
    icon_url: str | None = None
    wish_url: str | None = None
    local_icon: str | None = None
    local_wish: str | None = None
    extra_data: dict[str, Any] = Field(default_factory=dict)


class ItemCreate(ItemBase):
    game_id: int | None = None


class ItemUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    item_type: str | None = None
    rarity: int | None = None
    icon_url: str | None = None
    wish_url: str | None = None
    local_icon: str | None = None
    local_wish: str | None = None
    extra_data: dict[str, Any] | None = None


class ItemResponse(ItemBase):
    id: int | None = None
    game_id: int | None = None
    slug: str = ""
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Reward Schemas
# ============================================================================

class RewardBase(BaseModel):
    name: str
    rarity: int
    is_featured: bool
    extra_data: dict[str, Any] = Field(default_factory=dict)


class RewardCreate(RewardBase):
    item_id: int | None = None


class RewardUpdate(BaseModel):
    name: str | None = None
    rarity: int | None = None
    is_featured: bool | None = None
    extra_data: dict[str, Any] | None = None
    item_id: int | None = None


class RewardResponse(RewardBase):
    id: int | None = None
    banner_id: int | None = None
    item_id: int | None = None
    item: ItemResponse | None = None
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


class PaginatedBannerResponse(BaseModel):
    items: list[BannerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Game Schemas
# ============================================================================

class GameBase(BaseModel):
    name: str
    slug: str | None = None


class GameCreate(GameBase):
    pass


class GameUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class GameResponse(GameBase):
    id: int | None = None
    slug: str = ""
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


# ============================================================================
# Health Schemas
# ============================================================================

class DatabaseHealth(BaseModel):
    status: str = Field(description="Database connectivity status ('healthy' or 'unhealthy')")
    latency_ms: float | None = Field(default=None, description="Database ping latency in milliseconds")
    error: str | None = Field(default=None, description="Error message if database query failed")


class StorageHealth(BaseModel):
    status: str = Field(description="Storage status ('healthy', 'degraded', or 'unhealthy')")
    images_dir_writable: bool = Field(description="Whether the local image cache directory is writable")
    cached_images_count: int = Field(description="Total number of cached image assets on disk")
    cache_size_mb: float = Field(description="Total size of cached images in megabytes")
    free_disk_gb: float | None = Field(default=None, description="Free disk space in gigabytes on data drive")
    error: str | None = Field(default=None, description="Error message if disk inspection failed")


class HealthResponse(BaseModel):
    status: str = Field(description="Overall system health status ('ok', 'degraded', or 'unhealthy')")
    timestamp: datetime = Field(description="Current UTC timestamp of the health check")
    version: str = Field(default="1.0.0", description="API version")
    database: DatabaseHealth = Field(description="Database health details")
    storage: StorageHealth = Field(description="Disk and image cache storage health details")
    scheduler_active: bool = Field(description="Whether the background APScheduler is running")
    is_sync_running: bool = Field(description="Whether a banner scraping job is currently executing")

