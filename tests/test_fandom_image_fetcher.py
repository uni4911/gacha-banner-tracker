import pytest
from datetime import datetime, timezone
from pathlib import Path
from src.fetcher.fandom_image_fetcher import FandomImageFetcher
from src.models.models import Banner, BannerType, Reward


def test_fandom_image_fetcher_name_variations():
    fetcher = FandomImageFetcher()
    genshin_cand = fetcher._generate_candidate_titles("Genshin Impact", "Furina", is_character=True)
    assert "Furina_Icon.png" in genshin_cand["icon"]
    assert "Furina_Wish.png" in genshin_cand["wish"]

    hsr_cand = fetcher._generate_candidate_titles("Honkai: Star Rail", "Acheron", is_character=True)
    assert "Character_Acheron_Icon.png" in hsr_cand["icon"]
    assert "Character_Acheron_Splash_Art.png" in hsr_cand["wish"]

    wuwa_cand = fetcher._generate_candidate_titles("Wuthering Waves", "Jinhsi", is_character=True)
    assert "Resonator_Jinhsi.png" in wuwa_cand["icon"]
    assert "Jinhsi_Splash_Art.png" in wuwa_cand["wish"]


def test_fandom_image_fetcher_enrich_banner():
    fetcher = FandomImageFetcher()
    banner = Banner(
        version="4.2",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Furina", rarity=5, is_featured=True)],
        low_rate_rewards=[Reward(name="Bennett", rarity=4, is_featured=False)],
        start_date=datetime.now(timezone.utc),
        end_date=None,
        phase=1,
    )

    fetcher.enrich_banners([banner], "Genshin Impact", download_locally=False)

    furina = banner.limited_rewards[0]
    assert furina.extra_data is not None
    assert "icon_url" in furina.extra_data
    assert "wish_url" in furina.extra_data
    assert "Furina_Icon.png" in furina.extra_data["icon_url"]
    assert "Furina_Wish.png" in furina.extra_data["wish_url"]
