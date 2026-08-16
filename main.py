from src.fetcher.fetcher import (
    PrydwenBannerFetcher,
    GenshinBannerFetcher,
    StarrailBannerFetcher,
    WutheringWavesFetcher,
)
from src.fetcher.fandom_image_fetcher import FandomImageFetcher
from src.db.database import init_db
from src.db.service import save_banners_to_db

GAMES_TO_SCRAPE = [
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


def run_pipeline(download_images_locally: bool = True):
    init_db()
    image_fetcher = FandomImageFetcher()

    for game in GAMES_TO_SCRAPE:
        print(f"--> Scraping banners for {game['name']}...")
        fetcher = game["fetcher_cls"](game["url"], game["name"])
        game_banners = fetcher.fetch_banners()
        print(f"    Found {len(game_banners)} banners. Enriching images via Fandom Wiki...")
        image_fetcher.enrich_banners(
            game_banners, game["name"], download_locally=download_images_locally
        )
        save_banners_to_db(game_banners, game["name"])
        print(f"    Saved {len(game_banners)} banners for {game['name']}.")


if __name__ == "__main__":
    run_pipeline(download_images_locally=True)
