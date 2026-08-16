from src.db.models import GameModel, RewardModel, BannerModel
from src.db.database import SessionLocal
from src.db.mapper import BannerMapper
from src.models.models import Banner, Server
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import exists, select, or_
from datetime import datetime, timezone


def get_or_create_game(session: Session, game_name: str) -> GameModel:
    game = session.scalar(select(GameModel).where(GameModel.name == game_name))
    if not game:
        game = GameModel(name=game_name)
        session.add(game)
        session.flush()
    return game


def get_all_games() -> list[GameModel]:
    """Retrieve all games stored in the database."""
    with SessionLocal() as db:
        stmt = select(GameModel).order_by(GameModel.name.asc())
        return list(db.scalars(stmt).all())


def save_banners_to_db(banners: list[Banner], game_name: str) -> None:
    with SessionLocal() as db:
        game = get_or_create_game(db, game_name)
        for banner_data in banners:
            if not banner_data.limited_rewards:
                continue

            featured_name = banner_data.limited_rewards[0].name

            # Query existing banners for this game featuring the same character/weapon
            stmt = (
                select(BannerModel)
                .join(BannerModel.rewards)
                .where(
                    BannerModel.game_id == game.id,
                    RewardModel.name == featured_name,
                    RewardModel.is_featured.is_(True),
                )
                .options(selectinload(BannerModel.rewards))
            )
            existing_candidates = db.scalars(stmt).all()

            matched_banner: BannerModel | None = None
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
            else:
                banner_model = BannerMapper.to_model(banner_data, game_id=game.id)
                db.add(banner_model)
                db.flush()

        db.commit()


def get_active_banners(game_name: str, current_time: datetime, server: Server | None = None) -> list[Banner]:
    with SessionLocal() as db:
        stmt = (
            select(BannerModel)
            .join(GameModel)
            .where(
                GameModel.name == game_name,
            )
            .options(selectinload(BannerModel.rewards))
            .order_by(BannerModel.start_date.desc())
            .distinct()
        )
        banner_models = db.scalars(stmt).all()
        banners = [BannerMapper.to_domain(model) for model in banner_models]
        return [b for b in banners if b.is_active(current_time, server=server)]


def get_upcoming_banners(game_name: str, current_time: datetime, server: Server | None = None) -> list[Banner]:
    with SessionLocal() as db:
        stmt = (
            select(BannerModel)
            .join(GameModel)
            .where(
                GameModel.name == game_name,
            )
            .options(selectinload(BannerModel.rewards))
            .order_by(BannerModel.start_date.desc())
            .distinct()
        )
        banner_models = db.scalars(stmt).all()
        banners = [BannerMapper.to_domain(model) for model in banner_models]
        
        upcoming: list[Banner] = []
        for b in banners:
            if server is not None:
                start_tz = b.get_start_for_server(server)
                curr = (
                    current_time.astimezone(start_tz.tzinfo)
                    if current_time.tzinfo is not None
                    else current_time.replace(tzinfo=start_tz.tzinfo)
                )
                if start_tz > curr:
                    upcoming.append(b)
            else:
                start_utc = (
                    b.start_date
                    if b.start_date.tzinfo is not None
                    else b.start_date.replace(tzinfo=timezone.utc)
                )
                curr_utc = (
                    current_time.astimezone(timezone.utc)
                    if current_time.tzinfo is not None
                    else current_time.replace(tzinfo=timezone.utc)
                )
                if start_utc > curr_utc:
                    upcoming.append(b)
        return upcoming
    
def get_character_banner_history(game_name: str, character_name: str) -> list[Banner]:
    with SessionLocal() as db:
        stmt = (
            select(BannerModel)
            .join(BannerModel.game).join(BannerModel.rewards).
            where(
                GameModel.name == game_name,
                RewardModel.name == character_name
            )
        .options(selectinload(BannerModel.rewards))
        .order_by(BannerModel.start_date.desc())
        .distinct())
        banner_models = db.scalars(stmt).all()
        return [BannerMapper.to_domain(model) for model in banner_models]


def get_banners_by_version(game_name: str, version: str) -> list[Banner]:
    with SessionLocal() as db:
        stmt = (
            select(BannerModel)
            .join(BannerModel.game)
            .where(
                GameModel.name == game_name,
                BannerModel.version == version
            )
        ).options(selectinload(BannerModel.rewards))

        banner_models = db.scalars(stmt).all()
        return [BannerMapper.to_domain(model) for model in banner_models]
