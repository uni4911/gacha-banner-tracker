from __future__ import annotations
import re
from datetime import datetime, timezone, timedelta, tzinfo
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, JSON, Index


class BannerType(str, Enum):
    LIMITED_CHARACTER = "LIMITED_CHARACTER"
    LIMITED_WEAPON = "LIMITED_WEAPON"
    STANDARD_CHARACTER = "STANDARD_CHARACTER"
    STANDARD_WEAPON = "STANDARD_WEAPON"
    CHRONICLED = "CHRONICLED"
    STANDARD_WEAPON_AND_CHARACTER = "STANDARD_WEAPON_AND_CHARACTER"

    @classmethod
    def _missing_(cls, value: object) -> BannerType | None:
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper() or member.name.upper() == value.upper():
                    return member
        return None


class Server(str, Enum):
    ASIA = "ASIA"
    EUROPE = "EUROPE"
    AMERICA = "AMERICA"

    @classmethod
    def _missing_(cls, value: object) -> Server | None:
        if isinstance(value, str):
            val_upper = value.upper()
            if any(k in val_upper for k in ("ASIA", "SHANGHAI", "BEIJING", "TOKYO")):
                return cls.ASIA
            if any(k in val_upper for k in ("EUROPE", "PARIS", "BERLIN", "LONDON")):
                return cls.EUROPE
            if any(k in val_upper for k in ("AMERICA", "NEW_YORK", "NEW YORK", "LOS_ANGELES", "US")):
                return cls.AMERICA
        return None


SERVER_IANA_TIMEZONES: dict[Server, str] = {
    Server.ASIA: "Asia/Shanghai",
    Server.EUROPE: "Europe/Paris",
    Server.AMERICA: "America/New_York",
}

SERVER_FIXED_OFFSETS: dict[Server, timezone] = {
    Server.ASIA: timezone(timedelta(hours=8)),
    Server.EUROPE: timezone(timedelta(hours=1)),
    Server.AMERICA: timezone(timedelta(hours=-5)),
}


def get_server_timezone(server: Server) -> tzinfo:
    """Get the tzinfo for a game server, safely falling back to fixed UTC offsets."""
    iana_key = SERVER_IANA_TIMEZONES.get(server, "UTC")
    try:
        return ZoneInfo(iana_key)
    except (ZoneInfoNotFoundError, Exception):
        return SERVER_FIXED_OFFSETS.get(server, timezone.utc)


def slugify(text: str) -> str:
    """Convert a name to a clean URL-friendly slug (e.g. 'Honkai: Star Rail' -> 'honkai-star-rail')."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


class Base(DeclarativeBase):
    pass


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, default="")

    banners: Mapped[list[Banner]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        name: str = "",
        slug: str | None = None,
        banners: list[Banner] | None = None,
        id: int | None = None,
        **kwargs: Any,
    ):
        computed_slug = slug or slugify(name) if name else ""
        init_kwargs: dict[str, Any] = {"name": name, "slug": computed_slug, **kwargs}
        if banners is not None:
            init_kwargs["banners"] = banners
        if id is not None:
            init_kwargs["id"] = id
        super().__init__(**init_kwargs)


class Banner(Base):
    __tablename__ = "banners"
    __table_args__ = (
        Index("ix_banners_game_start_date", "game_id", "start_date"),
        Index("ix_banners_game_end_date", "game_id", "end_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id"), index=True, nullable=True)
    version: Mapped[str] = mapped_column(String(50), index=True)
    phase: Mapped[int] = mapped_column()
    banner_type: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[datetime] = mapped_column(index=True)
    end_date: Mapped[datetime | None] = mapped_column(index=True, nullable=True)

    game: Mapped[Game | None] = relationship(back_populates="banners")
    rewards: Mapped[list[Reward]] = relationship(
        back_populates="banner", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        version: str = "",
        banner_type: BannerType | str = BannerType.LIMITED_CHARACTER,
        limited_rewards: list[Reward] | None = None,
        low_rate_rewards: list[Reward] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        phase: int = 1,
        rewards: list[Reward] | None = None,
        game_id: int | None = None,
        id: int | None = None,
        **kwargs: Any,
    ):
        bt_str = banner_type.name if isinstance(banner_type, BannerType) else str(banner_type)
        all_rewards: list[Reward] = []
        if rewards is not None:
            all_rewards.extend(rewards)
        if limited_rewards is not None:
            all_rewards.extend(limited_rewards)
        if low_rate_rewards is not None:
            all_rewards.extend(low_rate_rewards)

        if start_date is not None and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date is not None and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        init_kwargs: dict[str, Any] = {
            "version": version,
            "phase": phase,
            "banner_type": bt_str,
            "start_date": start_date,
            "end_date": end_date,
            "rewards": all_rewards,
            **kwargs,
        }
        if game_id is not None:
            init_kwargs["game_id"] = game_id
        if id is not None:
            init_kwargs["id"] = id

        super().__init__(**init_kwargs)

    @property
    def limited_rewards(self) -> list[Reward]:
        return [r for r in self.rewards if r.is_featured]

    @property
    def low_rate_rewards(self) -> list[Reward]:
        return [r for r in self.rewards if not r.is_featured]

    def get_start_for_server(self, server: Server) -> datetime:
        """Calculate the exact start datetime in the specified server's timezone."""
        server_tz = get_server_timezone(server)
        start_date = self.start_date.date()

        if self.phase == 2:
            # Phase 2 starts at 18:00:00 local server time on the start date
            return datetime(start_date.year, start_date.month, start_date.day, 18, 0, 0, tzinfo=server_tz)
        else:
            # Phase 1 starts globally after maintenance (~06:00 UTC)
            start_utc = (
                self.start_date
                if self.start_date.tzinfo is not None
                else self.start_date.replace(tzinfo=timezone.utc)
            )
            return start_utc.astimezone(server_tz)

    def get_end_for_server(self, server: Server) -> datetime | None:
        """Calculate the exact end datetime in the specified server's timezone."""
        if self.end_date is None:
            return None

        server_tz = get_server_timezone(server)
        end_date = self.end_date.date()

        if self.phase == 1:
            # Phase 1 ends at 17:59:59 local server time on the end date
            return datetime(end_date.year, end_date.month, end_date.day, 17, 59, 59, tzinfo=server_tz)
        elif self.phase == 2:
            # Phase 2 ends at 14:59:59 local server time (before maintenance)
            return datetime(end_date.year, end_date.month, end_date.day, 14, 59, 59, tzinfo=server_tz)
        else:
            return datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=server_tz)

    def is_active(self, current_time: datetime, server: Server | None = None) -> bool:
        """Check if the banner is currently active at current_time (optionally for a specific server)."""
        if server is not None:
            start = self.get_start_for_server(server)
            end = self.get_end_for_server(server)
            server_tz = get_server_timezone(server)
            curr = (
                current_time.astimezone(server_tz)
                if current_time.tzinfo is not None
                else current_time.replace(tzinfo=server_tz)
            )
            return curr >= start and (end is None or curr <= end)

        start_date_aware = (
            self.start_date
            if self.start_date.tzinfo is not None
            else self.start_date.replace(tzinfo=timezone.utc)
        )
        curr = (
            current_time.astimezone(timezone.utc)
            if current_time.tzinfo is not None
            else current_time.replace(tzinfo=timezone.utc)
        )

        if self.end_date is None:
            return curr >= start_date_aware

        end_date_aware = (
            self.end_date
            if self.end_date.tzinfo is not None
            else self.end_date.replace(tzinfo=timezone.utc)
        )
        return curr >= start_date_aware and curr <= end_date_aware


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    banner_id: Mapped[int | None] = mapped_column(ForeignKey("banners.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    rarity: Mapped[int] = mapped_column()
    is_featured: Mapped[bool] = mapped_column()
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    banner: Mapped[Banner | None] = relationship(back_populates="rewards")

    def __init__(
        self,
        name: str = "",
        rarity: int = 4,
        is_featured: bool = False,
        extra_data: dict[str, Any] | None = None,
        banner_id: int | None = None,
        id: int | None = None,
        **kwargs: Any,
    ):
        init_kwargs: dict[str, Any] = {
            "name": name,
            "rarity": rarity,
            "is_featured": is_featured,
            "extra_data": dict(extra_data) if extra_data is not None else {},
            **kwargs,
        }
        if banner_id is not None:
            init_kwargs["banner_id"] = banner_id
        if id is not None:
            init_kwargs["id"] = id
        super().__init__(**init_kwargs)


# Backward compatibility aliases
GameModel = Game
BannerModel = Banner
RewardModel = Reward