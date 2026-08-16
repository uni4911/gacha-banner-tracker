from src.fetcher.fetcher import PrydwenBannerFetcher, GenshinBannerFetcher, StarrailBannerFetcher
from src.db.database import init_db
from src.db.service import save_banners_to_db

GAMES_TO_SCRAPE = [
    {
        "name": "Genshin Impact",
        "url": "https://www.prydwen.gg/genshin-impact/banners",
        "fetcher_cls": GenshinBannerFetcher
    },
    {
        "name": "Honkai: Star Rail",
        "url": "https://www.prydwen.gg/star-rail/banners",
        "fetcher_cls": StarrailBannerFetcher
    },
    {
            "name": "Wuthering Waves",
            "url": "https://www.prydwen.gg/wuthering-waves/banners",
            "fetcher_cls": StarrailBannerFetcher
    },
]


def run_pipeline():
    init_db()

    for game in GAMES_TO_SCRAPE:
        fetcher = game["fetcher_cls"](game["url"],game["name"])
        game_banners = fetcher.fetch_banners()
        save_banners_to_db(game_banners, game["name"])


if __name__ == "__main__":
    run_pipeline()
