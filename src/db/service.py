from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, or_

from src.db.models import Game, Reward, Banner, Item, Server, BannerType, slugify
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


def get_or_create_item(
    session: Session,
    game_id: int,
    name: str,
    rarity: int = 5,
    item_type: str = "CHARACTER",
    extra_data: dict[str, Any] | None = None,
    icon_url: str | None = None,
    wish_url: str | None = None,
    local_icon: str | None = None,
    local_wish: str | None = None,
) -> Item:
    """
    Retrieve an existing Item for a game by exact name or slug, or create a new one.
    Also merges any newly resolved image URLs or extra_data attributes.
    """
    clean_name = name.strip()
    clean_slug = slugify(clean_name)

    stmt = select(Item).where(
        Item.game_id == game_id,
        or_(
            Item.name == clean_name,
            Item.name.ilike(clean_name),
            Item.slug == clean_slug,
        ),
    )
    item = session.scalar(stmt)

    if item is None:
        item = Item(
            name=clean_name,
            game_id=game_id,
            slug=clean_slug,
            item_type=item_type,
            rarity=rarity,
            icon_url=icon_url,
            wish_url=wish_url,
            local_icon=local_icon,
            local_wish=local_wish,
            extra_data=extra_data or {},
        )
        session.add(item)
        session.flush()
    else:
        # Merge newly discovered images or extra_data
        if icon_url:
            item.icon_url = icon_url
        if wish_url:
            item.wish_url = wish_url
        if local_icon:
            item.local_icon = local_icon
        if local_wish:
            item.local_wish = local_wish
        if extra_data:
            merged = dict(item.extra_data or {})
            merged.update(extra_data)
            item.extra_data = merged
        if item_type and item_type != "CHARACTER" and item.item_type == "CHARACTER":
            item.item_type = item_type
        if rarity and rarity != item.rarity:
            item.rarity = rarity
        session.flush()

    return item


def get_game_items(
    game_identifier: str,
    item_type: str | None = None,
    rarity: int | None = None,
    db: Session | None = None,
) -> list[Item]:
    """Retrieve all unique items (characters, weapons, cards, etc.) registered for a game."""
    def _query(session: Session) -> list[Item]:
        stmt = (
            select(Item)
            .join(Item.game)
            .where(_game_filter(game_identifier))
        )
        if item_type is not None:
            stmt = stmt.where(Item.item_type.ilike(item_type.strip()))
        if rarity is not None:
            stmt = stmt.where(Item.rarity == rarity)

        stmt = stmt.order_by(Item.rarity.desc(), Item.name.asc())
        return list(session.scalars(stmt).all())

    if db is not None:
        return _query(db)
    with SessionLocal() as session:
        return _query(session)


def save_banners_to_db(banners: list[Banner], game_name: str, db: Session | None = None) -> None:
    def _save(session: Session) -> None:
        game = get_or_create_game(session, game_name)
        for banner_data in banners:
            if not banner_data.limited_rewards:
                continue

            featured_names = [
                r.name.strip() for r in banner_data.limited_rewards if r.name and r.name.strip()
            ]
            if not featured_names:
                continue

            # Query existing banners for this game featuring any of the same characters/weapons
            stmt = (
                select(Banner)
                .join(Banner.rewards)
                .where(
                    Banner.game_id == game.id,
                    Reward.name.in_(featured_names),
                    Reward.is_featured.is_(True),
                )
                .options(selectinload(Banner.rewards).selectinload(Reward.item))
            )
            existing_candidates = session.scalars(stmt).unique().all()

            target_bt = (
                banner_data.banner_type.name
                if isinstance(banner_data.banner_type, BannerType)
                else str(banner_data.banner_type)
            )

            matched_banner: Banner | None = None
            for eb in existing_candidates:
                eb_featured_names = {
                    r.name.strip() for r in eb.limited_rewards if r.name and r.name.strip()
                }
                eb_bt = (
                    eb.banner_type.name
                    if isinstance(eb.banner_type, BannerType)
                    else str(eb.banner_type)
                )

                # Check if banners are compatible (same banner type or overlapping featured items)
                is_compatible = (eb_bt == target_bt) or bool(eb_featured_names.intersection(featured_names))
                if not is_compatible:
                    continue

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

            def _resolve_item_for_reward(reward_obj: Reward) -> Item:
                is_weapon_banner = target_bt in (
                    BannerType.LIMITED_WEAPON.name,
                    BannerType.STANDARD_WEAPON.name,
                    "LIMITED_WEAPON",
                    "STANDARD_WEAPON",
                )
                inferred_type = "WEAPON" if is_weapon_banner else "CHARACTER"
                if reward_obj.extra_data and "item_type" in reward_obj.extra_data:
                    inferred_type = str(reward_obj.extra_data["item_type"])

                icon_url = reward_obj.extra_data.get("icon_url") if reward_obj.extra_data else None
                wish_url = reward_obj.extra_data.get("wish_url") if reward_obj.extra_data else None
                local_icon = reward_obj.extra_data.get("local_icon") if reward_obj.extra_data else None
                local_wish = reward_obj.extra_data.get("local_wish") if reward_obj.extra_data else None

                return get_or_create_item(
                    session=session,
                    game_id=game.id,
                    name=reward_obj.name,
                    rarity=reward_obj.rarity,
                    item_type=inferred_type,
                    extra_data=reward_obj.extra_data,
                    icon_url=icon_url,
                    wish_url=wish_url,
                    local_icon=local_icon,
                    local_wish=local_wish,
                )

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
                if banner_data.banner_type:
                    matched_banner.banner_type = target_bt

                # Update or add reward extra_data and ensure items are linked
                existing_rewards_by_name = {r.name: r for r in matched_banner.rewards}
                for new_reward in banner_data.rewards:
                    item = _resolve_item_for_reward(new_reward)
                    if new_reward.name in existing_rewards_by_name:
                        r_model = existing_rewards_by_name[new_reward.name]
                        updated_data = dict(r_model.extra_data or {})
                        if new_reward.extra_data:
                            updated_data.update(new_reward.extra_data)
                        r_model.extra_data = updated_data
                        r_model.rarity = new_reward.rarity
                        r_model.is_featured = new_reward.is_featured
                        r_model.item_id = item.id
                        r_model.item = item
                    else:
                        new_r = Reward(
                            name=new_reward.name,
                            rarity=new_reward.rarity,
                            is_featured=new_reward.is_featured,
                            extra_data=new_reward.extra_data,
                            banner_id=matched_banner.id,
                            item_id=item.id,
                            item=item,
                        )
                        matched_banner.rewards.append(new_r)
            else:
                # Add banner to session first so all attached rewards are part of session
                banner_data.game_id = game.id
                session.add(banner_data)
                session.flush()

                # Resolve all items for the new banner and assign item_id
                for r in banner_data.rewards:
                    item = _resolve_item_for_reward(r)
                    r.item_id = item.id

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
            .options(selectinload(Banner.rewards).selectinload(Reward.item))
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
            .options(selectinload(Banner.rewards).selectinload(Reward.item))
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
        clean_name = character_name.strip()
        stmt = (
            select(Banner)
            .join(Banner.game)
            .join(Banner.rewards)
            .outerjoin(Reward.item)
            .where(
                _game_filter(game_name),
                or_(
                    Reward.name == clean_name,
                    Reward.name.ilike(clean_name),
                    Item.name == clean_name,
                    Item.name.ilike(clean_name),
                    Item.slug == slugify(clean_name),
                ),
            )
            .options(selectinload(Banner.rewards).selectinload(Reward.item))
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
            .options(selectinload(Banner.rewards).selectinload(Reward.item))
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
            .options(selectinload(Banner.rewards).selectinload(Reward.item))
        )

        if version is not None:
            stmt = stmt.where(Banner.version == version)

        if phase is not None:
            stmt = stmt.where(Banner.phase == phase)

        if banner_type is not None:
            bt_str = banner_type.name if isinstance(banner_type, BannerType) else str(banner_type)
            stmt = stmt.where(Banner.banner_type == bt_str)

        if character_name is not None:
            clean_char = character_name.strip()
            stmt = stmt.join(Banner.rewards).outerjoin(Reward.item).where(
                or_(
                    Reward.name.ilike(f"%{clean_char}%"),
                    Item.name.ilike(f"%{clean_char}%"),
                    Item.slug.ilike(f"%{slugify(clean_char)}%"),
                )
            )

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

