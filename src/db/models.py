from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, JSON
from datetime import datetime
from typing import Any


class Base(DeclarativeBase):
    pass

class GameModel(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100),unique=True)

    banners: Mapped[list[BannerModel]] = relationship(back_populates="game")


class BannerModel(Base):
    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    version: Mapped[str] = mapped_column()
    phase: Mapped[int] = mapped_column()
    banner_type: Mapped[str] = mapped_column()
    start_date: Mapped[datetime] = mapped_column()
    end_date: Mapped[datetime] = mapped_column()

    game: Mapped[GameModel] = relationship(back_populates="banners")
    rewards: Mapped[list[RewardModel]] = relationship(back_populates="banner")


class RewardModel(Base):
    __tablename__ = "rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    banner_id: Mapped[int] = mapped_column(ForeignKey("banners.id"))
    name: Mapped[str] = mapped_column(String(100))
    rarity: Mapped[int] = mapped_column()
    is_featured: Mapped[bool] = mapped_column()
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON,default=dict)

    banner: Mapped[BannerModel] = relationship(back_populates="rewards")
    