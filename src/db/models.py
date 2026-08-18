from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, JSON, Index
from datetime import datetime
from typing import Any


class Base(DeclarativeBase):
    pass


class GameModel(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    banners: Mapped[list[BannerModel]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )


class BannerModel(Base):
    __tablename__ = "banners"
    __table_args__ = (
        Index("ix_banners_game_start_date", "game_id", "start_date"),
        Index("ix_banners_game_end_date", "game_id", "end_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    version: Mapped[str] = mapped_column(String(50), index=True)
    phase: Mapped[int] = mapped_column()
    banner_type: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[datetime] = mapped_column(index=True)
    end_date: Mapped[datetime | None] = mapped_column(index=True)

    game: Mapped[GameModel] = relationship(back_populates="banners")
    rewards: Mapped[list[RewardModel]] = relationship(
        back_populates="banner", cascade="all, delete-orphan"
    )


class RewardModel(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    banner_id: Mapped[int] = mapped_column(ForeignKey("banners.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    rarity: Mapped[int] = mapped_column()
    is_featured: Mapped[bool] = mapped_column()
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    banner: Mapped[BannerModel] = relationship(back_populates="rewards")
    