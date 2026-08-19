from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, or_

from src.db.models import Game, Reward, Banner, Server, BannerType, slugify
from src.db.database import SessionLocal


def _game_filter(identifier: str):
    """SQL filter helper matching game by exact slug, slugified name, or exact/case-insensitive name."""
    clean = identifier.strip()
    slug_cand = slugify(clean)
    return or_(
        Game.slug == clean,
        Game.slug == slug_cand,
        Game.name == clean,
        Game.name.ilike(clean),
    )


def get_game_by_name_or_slug(session: Session, identifier: str) -> Game | None:
    """Retrieve a Game entity by slug or name."""
    stmt = select(Game).where(_game_filter(identifier))
    return session.scalar(stmt)


def get_game(identifier: str, db: Session | None = None) -> Game | None:
    """Retrieve a single Game by slug or name."""
    if db is not None:
        return get_game_by_name_or_slug(db, identifier)
    with SessionLocal() as session:
        return get_game_by_name_or_slug(session, identifier)


def get_or_create_game(session: Session, game_name: str) -> Game:
    game = get_game_by_name_or_slug(session, game_name)
    if not game:
        game = Game(name=game_name, slug=slugify(game_name))
        session.add(game)
        session.flush()
    elif not game.slug:
        game.slug = slugify(game.name)
        session.flush()
    return game


def get_all_games(db: Session | None = None) -> list[Game]:
    """Retrieve all games stored in the database."""
    if db is not None:
        stmt = select(Game).order_by(Game.name.asc())
        return list(db.scalars(stmt).all())
    with SessionLocal() as session:
        stmt = select(Game).order_by(Game.name.asc())
        return list(session.scalars(stmt).all())


def save_banners_to_db(banners: list[Banner], game_name: str, db: Session | None = None) -> None:
    def _save(session: Session) -> None:
        game = get_or_create_game(session, game_name)
        for banner_data in banners:
            if not banner_data.limited_rewards:
                continue

            featured_name = banner_data.limited_rewards[0].name

            # Query existing banners for this game featuring the same character/weapon
            stmt = (
                select(Banner)
                .join(Banner.rewards)
                .where(
                    Banner.game_id == game.id,
                    Reward.name == featured_name,
                    Reward.is_featured.is_(True),
                )
                .options(selectinload(Banner.rewards))
            )
            existing_candidates = session.scalars(stmt).all()

            matched_banner: Banner | None = None
            for eb in existing_candidates:
                # 1. Match by version and phase (when version is known)
                if (
                    eb.version not in ("0.0", "Upcoming", "")
                    and banner_data.version not in ("0.0", "Upcoming", "")
                    and eb.version == banner_data.version
                    and eb.phase == banner_data.phase
                ):
                    matched_banner = eb
                    break

                # 2. Match by exact calendar start date
                if (
                    eb.start_date is not None
                    and banner_data.start_date is not None
                    and eb.start_date.date() == banner_data.start_date.date()
                ):
                    matched_banner = eb
                    break

                # 3. Match if version was previously 0.0/Upcoming and dates match within 1 day
                if (
                    (eb.version in ("0.0", "Upcoming") or banner_data.version in ("0.0", "Upcoming"))
                    and eb.start_date is not None
                    and banner_data.start_date is not None
                    and abs((eb.start_date.date() - banner_data.start_date.date()).days) <= 1
                ):
                    matched_banner = eb
                    break

            if matched_banner is not None:
                # Upgrade existing banner metadata with latest parsed values
                if banner_data.version not in ("0.0", "Upcoming"):
                    matched_banner.version = banner_data.version
                if banner_data.phase > 0:
                    matched_banner.phase = banner_data.phase
                if banner_data.start_date is not None:
                    matched_banner.start_date = banner_data.start_date
                if banner_data.end_date is not None:
                    matched_banner.end_date = banner_data.end_date

                # Update or add reward extra_data
                existing_rewards_by_name = {r.name: r for r in matched_banner.rewards}
                for new_reward in banner_data.rewards:
                    if new_reward.name in existing_rewards_by_name:
                        r_model = existing_rewards_by_name[new_reward.name]
                        updated_data = dict(r_model.extra_data or {})
                        if new_reward.extra_data:
                            updated_data.update(new_reward.extra_data)
                        r_model.extra_data = updated_data
                        r_model.rarity = new_reward.rarity
                        r_model.is_featured = new_reward.is_featured
                    else:
                        new_r = Reward(
                            name=new_reward.name,
                            rarity=new_reward.rarity,
                            is_featured=new_reward.is_featured,
                            extra_data=new_reward.extra_data,
                            banner_id=matched_banner.id,
                        )
                        matched_banner.rewards.append(new_r)
            else:
                banner_data.game_id = game.id
                session.add(banner_data)
                session.flush()

        session.commit()

    if db is not None:
        _save(db)
    else:
        with SessionLocal() as session:
            _save(session)


def get_active_banners(
    game_name: str,
    current_time: datetime,
    server: Server | None = None,
    db: Session | None = None,
) -> list[Banner]:
    def _query(session: Session) -> list[Banner]:
        curr_utc = (
            current_time.astimezone(timezone.utc)
            if current_time.tzinfo is not None
            else current_time.replace(tzinfo=timezone.utc)
        )

        # Buffer accounts for regional server time shifts (Asia, Europe, America)
        buffer = timedelta(days=1) if server is not None else timedelta(seconds=0)
        window_start = curr_utc - buffer
        window_end = curr_utc + buffer

        # SQL-level filter: database indexes filter out historical and future records directly
        stmt = (
            select(Banner)
            .join(Game)
            .where(
                _game_filter(game_name),
                Banner.start_date <= window_end,
                or_(
                    Banner.end_date.is_(None),
                    Banner.end_date >= window_start,
                ),
            )
            .options(selectinload(Banner.rewards))
            .order_by(Banner.start_date.desc())
            .distinct()
        )
        banner_models = session.scalars(stmt).all()
        active_banners = [b for b in banner_models if b.is_active(current_time, server=server)]

        if server is not None:
            adjusted: list[Banner] = []
            for b in active_banners:
                adjusted.append(
                    Banner(
                        version=b.version,
                        banner_type=b.banner_type,
                        rewards=b.rewards,
                        start_date=b.get_start_for_server(server),
                        end_date=b.get_end_for_server(server),
                        phase=b.phase,
                    )
                )
            return adjusted

        return active_banners

    if db is not None:
        return _query(db)
    with SessionLocal() as session:
        return _query(session)


def get_upcoming_banners(
    game_name: str,
    current_time: datetime,
    server: Server | None = None,
    db: Session | None = None,
) -> list[Banner]:
    def _query(session: Session) -> list[Banner]:
        curr_utc = (
            current_time.astimezone(timezone.utc)
            if current_time.tzinfo is not None
            else current_time.replace(tzinfo=timezone.utc)
        )

        # Buffer accounts for regional server time shifts
        buffer = timedelta(days=1) if server is not None else timedelta(seconds=0)
        min_start_date = curr_utc - buffer

        # SQL-level filter: excludes banners that already ended in the past
        stmt = (
            select(Banner)
            .join(Game)
            .where(
                _game_filter(game_name),
                Banner.start_date >= min_start_date,
            )
            .options(selectinload(Banner.rewards))
            .order_by(Banner.start_date.asc())
            .distinct()
        )
        banner_models = session.scalars(stmt).all()

        upcoming: list[Banner] = []
        for b in banner_models:
            if server is not None:
                start_tz = b.get_start_for_server(server)
                curr = (
                    current_time.astimezone(start_tz.tzinfo)
                    if current_time.tzinfo is not None
                    else current_time.replace(tzinfo=start_tz.tzinfo)
                )
                if start_tz > curr:
                    upcoming.append(
                        Banner(
                            version=b.version,
                            banner_type=b.banner_type,
                            rewards=b.rewards,
                            start_date=start_tz,
                            end_date=b.get_end_for_server(server),
                            phase=b.phase,
                        )
                    )
            else:
                start_utc = (
                    b.start_date
                    if b.start_date.tzinfo is not None
                    else b.start_date.replace(tzinfo=timezone.utc)
                )
                if start_utc > curr_utc:
                    upcoming.append(b)
        return upcoming

    if db is not None:
        return _query(db)
    with SessionLocal() as session:
        return _query(session)


def get_character_banner_history(
    game_name: str,
    character_name: str,
    db: Session | None = None,
) -> list[Banner]:
    def _query(session: Session) -> list[Banner]:
        stmt = (
            select(Banner)
            .join(Banner.game)
            .join(Banner.rewards)
            .where(
                _game_filter(game_name),
                Reward.name == character_name,
            )
            .options(selectinload(Banner.rewards))
            .order_by(Banner.start_date.desc())
            .distinct()
        )
        return list(session.scalars(stmt).all())

    if db is not None:
        return _query(db)
    with SessionLocal() as session:
        return _query(session)


def get_banners_by_version(
    game_name: str,
    version: str,
    db: Session | None = None,
) -> list[Banner]:
    def _query(session: Session) -> list[Banner]:
        stmt = (
            select(Banner)
            .join(Banner.game)
            .where(
                _game_filter(game_name),
                Banner.version == version,
            )
            .options(selectinload(Banner.rewards))
        )
        return list(session.scalars(stmt).all())

    if db is not None:
        return _query(db)
    with SessionLocal() as session:
        return _query(session)


def get_banners(
    game_identifier: str,
    version: str | None = None,
    phase: int | None = None,
    banner_type: BannerType | str | None = None,
    character_name: str | None = None,
    status: str = "all",  # "all" | "active" | "upcoming" | "ended"
    server: Server | None = None,
    current_time: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session | None = None,
) -> tuple[list[Banner], int]:
    """
    Unified query for listing banners with rich filtering, server timezone resolution, and pagination.
    Returns (banners_page, total_count).
    """
    def _query(session: Session) -> tuple[list[Banner], int]:
        target_time = current_time if current_time is not None else datetime.now(timezone.utc)
        curr_utc = (
            target_time.astimezone(timezone.utc)
            if target_time.tzinfo is not None
            else target_time.replace(tzinfo=timezone.utc)
        )

        stmt = (
            select(Banner)
            .join(Banner.game)
            .where(_game_filter(game_identifier))
            .options(selectinload(Banner.rewards))
        )

        if version is not None:
            stmt = stmt.where(Banner.version == version)

        if phase is not None:
            stmt = stmt.where(Banner.phase == phase)

        if banner_type is not None:
            bt_str = banner_type.name if isinstance(banner_type, BannerType) else str(banner_type)
            stmt = stmt.where(Banner.banner_type == bt_str)

        if character_name is not None:
            stmt = stmt.join(Banner.rewards).where(Reward.name.ilike(f"%{character_name.strip()}%"))

        stmt = stmt.order_by(Banner.start_date.desc()).distinct()
        raw_banners = list(session.scalars(stmt).all())

        # Filter by lifecycle status if requested
        filtered_banners: list[Banner] = []
        for b in raw_banners:
            if status == "active":
                if b.is_active(target_time, server=server):
                    filtered_banners.append(b)
            elif status == "upcoming":
                if server is not None:
                    st = b.get_start_for_server(server)
                    c = curr_utc.astimezone(st.tzinfo)
                    if st > c:
                        filtered_banners.append(b)
                else:
                    st = b.start_date if b.start_date.tzinfo is not None else b.start_date.replace(tzinfo=timezone.utc)
                    if st > curr_utc:
                        filtered_banners.append(b)
            elif status == "ended":
                if server is not None:
                    et = b.get_end_for_server(server)
                    if et is not None:
                        c = curr_utc.astimezone(et.tzinfo)
                        if et < c:
                            filtered_banners.append(b)
                else:
                    if b.end_date is not None:
                        et = b.end_date if b.end_date.tzinfo is not None else b.end_date.replace(tzinfo=timezone.utc)
                        if et < curr_utc:
                            filtered_banners.append(b)
            else:
                filtered_banners.append(b)

        # Server-adjust dates if server is requested
        if server is not None:
            adjusted: list[Banner] = []
            for b in filtered_banners:
                adjusted.append(
                    Banner(
                        version=b.version,
                        banner_type=b.banner_type,
                        rewards=b.rewards,
                        start_date=b.get_start_for_server(server),
                        end_date=b.get_end_for_server(server),
                        phase=b.phase,
                        game_id=b.game_id,
                        id=b.id,
                    )
                )
            filtered_banners = adjusted

        total = len(filtered_banners)
        start_idx = max(0, (page - 1) * page_size)
        end_idx = start_idx + page_size
        paged_banners = filtered_banners[start_idx:end_idx]

        return paged_banners, total

    if db is not None:
        return _query(db)
    with SessionLocal() as session:
        return _query(session)

