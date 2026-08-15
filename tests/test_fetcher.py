from unittest.mock import patch
import pytest
from src.fetcher.fetcher import GenshinBannerFetcher

@pytest.fixture
def mock_genshin_html() -> str:
    return """
    <section class="section-group">
        <h3>Patch 5.0 Phase 1</h3>
        <article class="banner-card">
            <p class="banner-name">Mualani</p>
            <div class="featured-rate-ups">
                <a class="featured-rate-up">Kachina</a>
                <a class="featured-rate-up">Bennett</a>
                <a class="featured-rate-up">Xinyan</a>
            </div>
            <strong data-banner-range="true">Jan 01, 2026 – Jan 21, 2026</strong>
        </article>
    </section>
    """

@patch.object(GenshinBannerFetcher, "_get_html")
def test_fetch_banners_succses(mock_get_html, mock_genshin_html):

    mock_get_html.return_value = mock_genshin_html

    genshin_fetcher = GenshinBannerFetcher(mock_genshin_html, "Genshin Impact")
    banners = genshin_fetcher.fetch_banners()

    assert len(banners) == 1
    assert banners[0].version == "5.0"
    assert banners[0].phase == 1
    assert banners[0].limited_rewards[0].name == "Mualani"
    assert banners[0].limited_rewards[0].rarity == 5
    assert banners[0].limited_rewards[0].is_featured is True
    four_star_names = [reward.name for reward in banners[0].low_rate_rewards]
    assert "Kachina" in four_star_names