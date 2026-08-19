from unittest.mock import patch
import pytest
from src.db.models import BannerType
from src.fetcher.fetcher import (
    GenshinBannerFetcher,
    ZenlessZoneZeroFetcher,
    NevernessToEvernessFetcher,
)

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
def test_fetch_banners_success(mock_get_html, mock_genshin_html):

    mock_get_html.return_value = mock_genshin_html

    genshin_fetcher = GenshinBannerFetcher(mock_genshin_html, "Genshin Impact")
    banners = genshin_fetcher.fetch_banners()

    assert len(banners) == 1
    assert banners[0].version == "5.0"
    assert banners[0].phase == 1
    assert banners[0].limited_rewards[0].name == "Mualani"
    assert banners[0].limited_rewards[0].rarity == 5
    assert banners[0].limited_rewards[0].is_featured is True
    # Phase 1 timing checks: starts at 06:00 UTC, ends at 17:59:59 UTC
    assert banners[0].start_date.hour == 6
    assert banners[0].end_date.hour == 17
    assert banners[0].end_date.minute == 59
    assert banners[0].end_date.second == 59
    four_star_names = [reward.name for reward in banners[0].low_rate_rewards]
    assert "Kachina" in four_star_names


@patch.object(GenshinBannerFetcher, "_get_html")
def test_fetch_banners_phase2_timing(mock_get_html):
    html = """
    <section class="section-group">
        <h3>Patch 5.0 Phase 2</h3>
        <article class="banner-card">
            <p class="banner-name">Kinich</p>
            <div class="featured-rate-ups">
                <a class="featured-rate-up">Chevreuse</a>
            </div>
            <strong data-banner-range="true">Jan 21, 2026 – Feb 11, 2026</strong>
        </article>
    </section>
    """
    mock_get_html.return_value = html
    fetcher = GenshinBannerFetcher("https://dummy.url", "Genshin Impact")
    banners = fetcher.fetch_banners()

    assert len(banners) == 1
    assert banners[0].phase == 2
    # Phase 2 starts at 18:00 UTC and ends at 14:59:59 UTC
    assert banners[0].start_date.hour == 18
    assert banners[0].end_date.hour == 14
    assert banners[0].end_date.minute == 59
    assert banners[0].end_date.second == 59


@patch.object(GenshinBannerFetcher, "_get_html")
def test_fetch_banners_weapon_keyword_fallback(mock_get_html):
    from src.db.models import BannerType
    html = """
    <section class="section-group">
        <h3>Patch 5.0 Phase 1</h3>
        <article class="banner-card">
            <p class="banner-name">Epitome Invocation (Weapon Banner)</p>
            <div class="featured-rate-ups"></div>
            <strong data-banner-range="true">Jan 01, 2026 – Jan 21, 2026</strong>
        </article>
    </section>
    """
    mock_get_html.return_value = html
    fetcher = GenshinBannerFetcher("https://dummy.url", "Genshin Impact")
    banners = fetcher.fetch_banners()

    assert len(banners) == 1
    assert banners[0].banner_type == BannerType.LIMITED_WEAPON


@patch.object(ZenlessZoneZeroFetcher, "_get_html")
def test_zzz_fetcher_success(mock_get_html):
    html = """
    <section class="section-group">
        <h3>Patch 3.1 Phase 1</h3>
        <article class="banner-card character-banner-card">
            <p class="banner-name">Aria</p>
            <div class="featured-rate-ups"></div>
            <strong data-banner-range="true">Jul 29, 2026 – Aug 19, 2026</strong>
        </article>
        <article class="banner-card weapon-banner-card light-cone-card">
            <p class="banner-name">Angel in the Shell</p>
            <div class="featured-rate-ups"></div>
            <strong data-banner-range="true">Jul 29, 2026 – Aug 19, 2026</strong>
        </article>
    </section>
    """
    mock_get_html.return_value = html
    fetcher = ZenlessZoneZeroFetcher("https://dummy.url", "Zenless Zone Zero")
    banners = fetcher.fetch_banners()

    assert len(banners) == 2
    assert banners[0].version == "3.1"
    assert banners[0].phase == 1
    assert banners[0].limited_rewards[0].name == "Aria"
    assert banners[0].banner_type == BannerType.LIMITED_CHARACTER
    assert banners[1].limited_rewards[0].name == "Angel in the Shell"
    assert banners[1].banner_type == BannerType.LIMITED_WEAPON


@patch.object(NevernessToEvernessFetcher, "_get_html")
def test_nte_fetcher_success(mock_get_html):
    html = """
    <section class="section-group">
        <h3>Patch 1.3 Phase 1</h3>
        <article class="banner-card character-banner-card">
            <p class="banner-name">Nanally</p>
            <div class="featured-rate-ups"></div>
            <strong data-banner-range="true">Aug 19, 2026 – Sep 09, 2026</strong>
        </article>
        <article class="banner-card weapon-banner-card light-cone-card">
            <p class="banner-name">Ravenous Blade</p>
            <div class="featured-rate-ups"></div>
            <strong data-banner-range="true">Aug 19, 2026 – Sep 09, 2026</strong>
        </article>
    </section>
    """
    mock_get_html.return_value = html
    fetcher = NevernessToEvernessFetcher("https://dummy.url", "Neverness to Everness")
    banners = fetcher.fetch_banners()

    assert len(banners) == 2
    assert banners[0].version == "1.3"
    assert banners[0].phase == 1
    assert banners[0].limited_rewards[0].name == "Nanally"
    assert banners[0].banner_type == BannerType.LIMITED_CHARACTER
    assert banners[1].limited_rewards[0].name == "Ravenous Blade"
    assert banners[1].banner_type == BannerType.LIMITED_WEAPON