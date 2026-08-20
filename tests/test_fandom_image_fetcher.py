from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from src.fetcher.fandom_image_fetcher import FandomImageFetcher
from src.models.models import Banner, BannerType, Reward


def test_fandom_image_fetcher_name_variations():
    fetcher = FandomImageFetcher()
    genshin_cand = fetcher._generate_candidate_titles("Genshin Impact", "Furina", is_character=True)
    assert "Furina_Icon.png" in genshin_cand["icon"]
    assert "Character_Furina_Full_Wish.png" in genshin_cand["wish"]

    hsr_cand = fetcher._generate_candidate_titles("Honkai: Star Rail", "Acheron", is_character=True)
    assert "Character_Acheron_Icon.png" in hsr_cand["icon"]
    assert "Character_Acheron_Splash_Art.png" in hsr_cand["wish"]

    wuwa_cand = fetcher._generate_candidate_titles("Wuthering Waves", "Jinhsi", is_character=True)
    assert "Resonator_Jinhsi.png" in wuwa_cand["icon"]
    assert "Jinhsi_Splash_Art.png" in wuwa_cand["wish"]

    # ZZZ Agent Portrait tests
    zzz_cand = fetcher._generate_candidate_titles("Zenless Zone Zero", "Ellen Joe", is_character=True)
    assert "Agent_Ellen_Joe_Icon.png" in zzz_cand["icon"]
    assert "Agent_Ellen_Joe_Portrait.png" in zzz_cand["wish"]
    assert zzz_cand["wish"][0] == "Agent_Ellen_Joe_Portrait.png"

    # Dynamic MediaWiki ranking tests
    sample_files = [
        "Agent Claret Flint Agent Record.png",
        "Agent Claret Flint Portrait.png",
        "Agent Claret Flint Icon.png",
        "VO Claret Assist.ogg",
    ]
    ranked = fetcher._rank_dynamic_files(sample_files, "Zenless Zone Zero", is_character=True)
    assert "Agent Claret Flint Portrait.png" in ranked["wish"]
    assert "Agent Claret Flint Icon.png" in ranked["icon"]
    assert "VO Claret Assist.ogg" not in ranked["wish"]

    # NTE Full Body Portrait tests
    nte_cand = fetcher._generate_candidate_titles("Neverness to Everness", "Nanally", is_character=True)
    assert "Nanally_Portrait.png" in nte_cand["wish"]
    assert nte_cand["wish"][0] == "Nanally_Portrait.png"

    nte_mint = fetcher._generate_candidate_titles("Neverness to Everness", "Mint", is_character=True)
    assert "Mint_Portrait.png" in nte_mint["wish"]
    assert nte_mint["wish"][0] == "Mint_Portrait.png"





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

    mock_batch_results = {
        "Furina_Icon.png": "https://static.wikia.nocookie.net/gensin-impact/images/Furina_Icon.png",
        "Character_Furina_Full_Wish.png": "https://static.wikia.nocookie.net/gensin-impact/images/Character_Furina_Full_Wish.png",
        "Bennett_Icon.png": "https://static.wikia.nocookie.net/gensin-impact/images/Bennett_Icon.png",
    }

    with patch.object(fetcher, "query_fandom_batch", return_value=mock_batch_results):
        fetcher.enrich_banners([banner], "Genshin Impact", download_locally=False)

    furina = banner.limited_rewards[0]
    assert furina.extra_data is not None
    assert "icon_url" in furina.extra_data
    assert "wish_url" in furina.extra_data
    assert "Furina_Icon.png" in furina.extra_data["icon_url"]
    assert "Character_Furina_Full_Wish.png" in furina.extra_data["wish_url"]


def test_fandom_image_fetcher_enrich_banner_with_local_download(tmp_path):
    fetcher = FandomImageFetcher(cache_dir=tmp_path)
    banner = Banner(
        version="4.2",
        banner_type=BannerType.LIMITED_CHARACTER,
        limited_rewards=[Reward(name="Furina", rarity=5, is_featured=True)],
        low_rate_rewards=[],
        start_date=datetime.now(timezone.utc),
        end_date=None,
        phase=1,
    )

    mock_batch_results = {
        "Furina_Icon.png": "https://example.com/Furina_Icon.png",
        "Character_Furina_Full_Wish.png": "https://example.com/Character_Furina_Full_Wish.png",
    }

    mock_download_results = {
        "https://example.com/Furina_Icon.png": True,
        "https://example.com/Character_Furina_Full_Wish.png": True,
    }

    with patch.object(fetcher, "query_fandom_batch", return_value=mock_batch_results), \
         patch.object(fetcher, "download_images_concurrently", return_value=mock_download_results):
        fetcher.enrich_banners([banner], "Genshin Impact", download_locally=True)

    furina = banner.limited_rewards[0]
    assert "local_icon" in furina.extra_data
    assert "local_wish" in furina.extra_data
    assert furina.extra_data["local_icon"] == "/static/images/genshin_impact/furina_icon.png"
    assert furina.extra_data["local_wish"] == "/static/images/genshin_impact/furina_wish.png"


def test_fandom_image_fetcher_query_batch_api():
    fetcher = FandomImageFetcher()

    mock_api_json = {
        "query": {
            "pages": {
                "123": {
                    "title": "File:Furina_Icon.png",
                    "imageinfo": [{"url": "https://static.wikia.nocookie.net/Furina_Icon.png"}],
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_api_json

    with patch.object(fetcher.session, "get", return_value=mock_resp):
        urls = fetcher.query_fandom_batch("genshin-impact", ["Furina_Icon.png"])

    assert "Furina_Icon.png" in urls
    assert urls["Furina_Icon.png"] == "https://static.wikia.nocookie.net/Furina_Icon.png"


@pytest.mark.anyio
async def test_download_images_async(tmp_path):
    fetcher = FandomImageFetcher(cache_dir=tmp_path)
    target1 = tmp_path / "img1.png"
    target2 = tmp_path / "img2.png"
    tasks = [
        ("https://example.com/img1.png", target1),
        ("https://example.com/img2.png", target2),
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake_image_bytes"

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        results = await fetcher.download_images_async(tasks, max_concurrency=2)

    assert results["https://example.com/img1.png"] is True
    assert results["https://example.com/img2.png"] is True
    assert target1.exists()
    assert target1.read_bytes() == b"fake_image_bytes"
    assert target2.exists()
    assert target2.read_bytes() == b"fake_image_bytes"


def test_download_images_concurrently_sync_wrapper(tmp_path):
    fetcher = FandomImageFetcher(cache_dir=tmp_path)
    target = tmp_path / "img_sync.png"
    tasks = [("https://example.com/img_sync.png", target)]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"sync_bytes"

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        results = fetcher.download_images_concurrently(tasks)

    assert results["https://example.com/img_sync.png"] is True
    assert target.exists()
    assert target.read_bytes() == b"sync_bytes"


def test_weapon_icon_ranking_and_prydwen_fallback():
    fetcher = FandomImageFetcher()
    filenames = [
        "Weapon Whitelake Frostfeather.png",
        "Weapon Whitelake Frostfeather 2nd.png",
        "Whitelake Frostfeather Wallpaper.png",
    ]
    ranked = fetcher._rank_dynamic_files(filenames, "Genshin Impact", is_character=False)
    assert "Weapon Whitelake Frostfeather.png" in ranked["icon"]

    # Test Prydwen art fallback when Fandom has no icon
    banner = Banner(
        version="3.6",
        banner_type=BannerType.LIMITED_WEAPON,
        limited_rewards=[
            Reward(
                name="Glint of Clouds",
                rarity=5,
                is_featured=True,
                extra_data={"prydwen_art": "https://cdn.prydwen.gg/weapons/glint.webp"},
            )
        ],
        low_rate_rewards=[],
        start_date=datetime.now(timezone.utc),
        end_date=None,
        phase=1,
    )

    with patch.object(fetcher, "query_fandom_batch", return_value={}):
        fetcher.enrich_banners([banner], "Wuthering Waves", download_locally=False)

    glint = banner.limited_rewards[0]
    assert glint.extra_data.get("wish_url") == "https://cdn.prydwen.gg/weapons/glint.webp"
    assert glint.extra_data.get("icon_url") == "https://cdn.prydwen.gg/weapons/glint.webp"


