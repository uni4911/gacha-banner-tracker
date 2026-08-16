from __future__ import annotations
from datetime import datetime, timezone, timedelta, tzinfo
from enum import Enum, auto
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any

class BannerType(Enum):
    LIMITED_CHARACTER = auto()
    LIMITED_WEAPON = auto()
    STANDARD_CHARACTER =auto()
    STANDARD_WEAPON = auto()
    CHRONICLED = auto()
    STANDARD_WEAPON_AND_CHARACTER = auto()

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

# Standard fixed server timezone offsets used in gacha games (HoYoverse servers do not observe DST)
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

@dataclass
class Banner:
    version: str 
    banner_type: BannerType 
    limited_rewards: list[Reward] 
    low_rate_rewards: list[Reward]
    start_date: datetime
    end_date: datetime|None
    phase: int

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

    @property
    def rewards(self) -> list[Reward]:
        return self.limited_rewards + self.low_rate_rewards

@dataclass
class Reward:
    name: str
    rarity: int
    is_featured: bool
    extra_data: dict[str, Any] = field(default_factory=dict)

@dataclass
class Game:
    name: str
    banners: list[Banner] = field(default_factory=list)