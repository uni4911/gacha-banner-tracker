from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum, auto
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
from typing import Any

class BannerType(Enum):
    LIMITED_CHARACTER = auto()
    LIMITED_WEAPON = auto()
    STANDARD_CHARACTER =auto()
    STANDARD_WEAPON = auto()
    CHRONICLED = auto()
    STANDARD_WEAPON_AND_CHARACTER = auto()

class Server(Enum):
    ASIA = "Asia/Shanghai"
    EUROPE = "Europe/Paris"
    AMERICA = "America/New_York"

@dataclass
class Banner:
    version: str 
    banner_type: BannerType 
    limited_rewards: list[Reward] 
    low_rate_rewards: list[Reward]
    start_date: datetime
    end_date: datetime|None
    phase: int

    def is_active(self, current_time: datetime) -> bool:
        return self.start_date <= current_time <= self.end_date 

    def get_start_for_server(self, server: Server) -> datetime:
        utc_time = self.start_date.astimezone(timezone.utc)
        return utc_time.astimezone(ZoneInfo(server.value))

@dataclass
class Reward:
    name: str
    rarity: int
    is_featured: bool
    extra_data: dict[str, Any] = field(default_factory=dict)