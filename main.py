from src.fetcher.fetcher import GenshinBannerFetcher

genshin_fetcher = GenshinBannerFetcher()
genshin_banners = genshin_fetcher.fetch_banners()

print(genshin_banners)

