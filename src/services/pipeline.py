from __future__ import annotations
import logging
from typing import Any

from src.fetcher.fetcher import (
    GenshinBannerFetcher,
    StarrailBannerFetcher,
    WutheringWavesFetcher,
)
from src.fetcher.fandom_image_fetcher import FandomImageFetcher
from src.db.database import init_db
from src.db.service import save_banners_to_db

logger = logging.getLogger(__name__)

GAMES_TO_SCRAPE: list[dict[str, Any]] = [
    {
        "name": "Genshin Impact",
        "url": "https://www.prydwen.gg/genshin-impact/banners",
        "fetcher_cls": GenshinBannerFetcher,
    },
    {
        "name": "Honkai: Star Rail",
        "url": "https://www.prydwen.gg/star-rail/banners",
        "fetcher_cls": StarrailBannerFetcher,
    },
    {
        "name": "Wuthering Waves",
        "url": "https://www.prydwen.gg/wuthering-waves/banners",
        "fetcher_cls": WutheringWavesFetcher,
    },
]


def run_pipeline(
    game_names: list[str] | None = None,
    download_images_locally: bool = True,
) -> dict[str, int]:
    """
    Executes the banner scraping, image enrichment, and database persistence pipeline.

    Args:
        game_names: Optional list of game names to scrape. If None, scrapes all registered games.
        download_images_locally: Whether to download artwork and icons to local disk.

    Returns:
        Dictionary mapping game name to number of banners saved.
    """
    init_db()
    image_fetcher = FandomImageFetcher()
    results: dict[str, int] = {}

    target_games = (
        [g for g in GAMES_TO_SCRAPE if g["name"] in game_names]
        if game_names is not None
        else GAMES_TO_SCRAPE
    )

    for game in target_games:
        game_name = game["name"]
        logger.info(f"--> Scraping banners for {game_name}...")
        try:
            fetcher = game["fetcher_cls"](game["url"], game_name)
            game_banners = fetcher.fetch_banners()
            logger.info(
                f"    Found {len(game_banners)} banners for {game_name}. Enriching images via Fandom Wiki..."
            )
            image_fetcher.enrich_banners(
                game_banners, game_name, download_locally=download_images_locally
            )
            save_banners_to_db(game_banners, game_name)
            results[game_name] = len(game_banners)
            logger.info(f"    Saved {len(game_banners)} banners for {game_name}.")
        except Exception as exc:
            logger.error(f"Failed to scrape banners for {game_name}: {exc}", exc_info=True)
            raise exc

    return results
