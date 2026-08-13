from src.fetcher.fetcher import GenshinBannerFetcher
from src.db.database import init_db
from src.db.service import save_banners_to_db

init_db()

genshin_fetcher = GenshinBannerFetcher()
genshin_banners = genshin_fetcher.fetch_banners()

save_banners_to_db(genshin_banners, "Genshin Impact")

