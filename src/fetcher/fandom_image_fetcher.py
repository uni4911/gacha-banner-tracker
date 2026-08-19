import asyncio
import concurrent.futures
import logging
import re
from pathlib import Path
from typing import Any
import httpx
from curl_cffi import requests
from src.db.models import Banner, Reward, BannerType

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGE_CACHE_DIR = PROJECT_ROOT / "data" / "images"

WIKI_SUBDOMAINS: dict[str, str] = {
    "Genshin Impact": "genshin-impact",
    "Honkai: Star Rail": "honkai-star-rail",
    "Wuthering Waves": "wutheringwaves",
    "Zenless Zone Zero": "zenless-zone-zero",
    "Neverness to Everness": "neverness-to-everness",
}


class FandomImageFetcher:
    """Fetches high-resolution character icons and wish/splash art from Fandom Wikis using MediaWiki API."""

    def __init__(self, cache_dir: Path | None = None, max_concurrency: int = 10):
        self.cache_dir = cache_dir or IMAGE_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrency = max_concurrency
        self.session = requests.Session(impersonate="chrome120")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.session.headers.update(self.headers)

    def _get_wiki_subdomain(self, game_name: str) -> str:
        return WIKI_SUBDOMAINS.get(game_name, game_name.lower().replace(" ", "-").replace(":", ""))

    def _get_name_variations(self, name: str) -> list[str]:
        """Generate common spelling/alias variations for a character or weapon name."""
        cleaned = re.sub(r"\s+", " ", name.strip())
        variations = [cleaned]

        # Handle bullet separation (e.g. Himeko Nova -> Himeko • Nova)
        parts = cleaned.split()
        if len(parts) == 2 and "•" not in cleaned:
            variations.append(f"{parts[0]} • {parts[1]}")
            variations.append(parts[0])  # Base name fallback (e.g. Himeko)
        elif len(parts) >= 3 and "•" not in cleaned:
            variations.append(f"{parts[0]} • {' '.join(parts[1:])}")
            variations.append(f"{' '.join(parts[:2])} • {' '.join(parts[2:])}")
            variations.append(" ".join(parts[:2]))
            variations.append(parts[0])

        if "•" in cleaned:
            variations.append(cleaned.replace("•", " ").replace("  ", " ").strip())
            variations.append(cleaned.split("•")[0].strip())

        # Handle 'The Shorekeeper' <-> 'Shorekeeper'
        if cleaned.lower().startswith("the "):
            variations.append(cleaned[4:].strip())
        else:
            variations.append(f"The {cleaned}")

        # Handle '&' <-> 'and'
        if "&" in cleaned:
            variations.append(cleaned.replace("&", "and"))
        elif " and " in cleaned:
            variations.append(cleaned.replace(" and ", " & "))

        # Handle dot removal (e.g. Dr. Ratio <-> Dr Ratio)
        if "." in cleaned:
            variations.append(cleaned.replace(".", ""))

        # Deduplicate while preserving order
        seen = set()
        result = []
        for v in variations:
            if v and v not in seen:
                seen.add(v)
                result.append(v)
        return result

    def _generate_candidate_titles(
        self, game_name: str, item_name: str, is_character: bool = True
    ) -> dict[str, list[str]]:
        """Generate candidate wiki filenames for icons and wish/splash art across name variations."""
        wiki = self._get_wiki_subdomain(game_name)
        candidates: dict[str, list[str]] = {"icon": [], "wish": []}
        name_variants = self._get_name_variations(item_name)

        for name in name_variants:
            name_u = name.replace(" ", "_")

            if "genshin" in wiki:
                if is_character:
                    candidates["icon"].extend([
                        f"{name_u}_Icon.png",
                        f"{name_u}_Side_Icon.png",
                        f"Character_{name_u}_Icon.png",
                        f"{name_u}_Item.png",
                    ])
                    candidates["wish"].extend([
                        f"{name_u}_Wish.png",
                        f"{name_u}_Multi_Wish.png",
                        f"Character_{name_u}_Wish.png",
                    ])
                else:
                    candidates["icon"].extend([
                        f"Weapon_{name_u}.png",
                        f"Weapon_{name_u}_2nd.png",
                        f"{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"Weapon_{name_u}_Wish.png",
                        f"Weapon_{name_u}.png",
                    ])

            elif "star-rail" in wiki:
                if is_character:
                    candidates["icon"].extend([
                        f"Character_{name_u}_Icon.png",
                        f"{name_u}_Icon.png",
                        f"Character_{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"Character_{name_u}_Splash_Art.png",
                        f"{name_u}_Splash_Art.png",
                        f"Character_{name_u}_Wish.png",
                        f"Character_{name_u}_Introduction.png",
                    ])
                else:
                    candidates["icon"].extend([
                        f"Light_Cone_{name_u}_Icon.png",
                        f"Light_Cone_{name_u}.png",
                        f"{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"Light_Cone_{name_u}_Art.png",
                        f"Light_Cone_{name_u}.png",
                    ])

            elif "wuthering" in wiki:
                if is_character:
                    candidates["icon"].extend([
                        f"Resonator_{name_u}.png",
                        f"{name_u}_Icon.png",
                        f"{name_u}Card.png",
                        f"{name_u}_Card.png",
                    ])
                    candidates["wish"].extend([
                        f"{name_u}_Splash_Art.png",
                        f"{name_u}_Convene_Draw.png",
                        f"{name_u}_Convene_Still.png",
                        f"{name_u}_Full_Sprite.png",
                    ])
                else:
                    candidates["icon"].extend([
                        f"Weapon_{name_u}.png",
                        f"{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"{name_u}_Splash_Art.png",
                        f"{name_u}.png",
                    ])

            elif "zenless" in wiki:
                if is_character:
                    candidates["icon"].extend([
                        f"Agent_{name_u}_Icon.png",
                        f"Agent_{name_u}_Portrait.png",
                        f"Agent_{name_u}.png",
                        f"Bangboo_{name_u}_Icon.png",
                        f"Bangboo_{name_u}.png",
                        f"{name_u}_Icon.png",
                        f"Character_{name_u}_Icon.png",
                        f"{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"Agent_{name_u}_Mindscape_Cinema.png",
                        f"Agent_{name_u}_Full.png",
                        f"Agent_{name_u}_Splash_Art.png",
                        f"Agent_{name_u}_Portrait.png",
                        f"{name_u}_Full.png",
                        f"{name_u}_Splash_Art.png",
                        f"{name_u}_Wish.png",
                        f"Bangboo_{name_u}.png",
                    ])
                else:
                    candidates["icon"].extend([
                        f"W-Engine_{name_u}_Icon.png",
                        f"W-Engine_{name_u}.png",
                        f"W_Engine_{name_u}.png",
                        f"Item_{name_u}.png",
                        f"{name_u}_Icon.png",
                        f"{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"W-Engine_{name_u}.png",
                        f"W-Engine_{name_u}_Art.png",
                        f"W_Engine_{name_u}.png",
                        f"{name_u}_Art.png",
                        f"{name_u}.png",
                    ])

            elif "neverness" in wiki:
                if is_character:
                    candidates["icon"].extend([
                        f"{name_u}_Icon.png",
                        f"Character_{name_u}_Icon.png",
                        f"Esper_{name_u}_Icon.png",
                        f"Agent_{name_u}_Icon.png",
                        f"{name_u}.png",
                        f"Character_{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"{name_u}_Splash_Art.png",
                        f"{name_u}_Full.png",
                        f"{name_u}_Card.png",
                        f"{name_u}_Portrait.png",
                        f"{name_u}.png",
                        f"Character_{name_u}_Splash_Art.png",
                        f"Character_{name_u}.png",
                    ])
                else:
                    candidates["icon"].extend([
                        f"Weapon_{name_u}_Icon.png",
                        f"Weapon_{name_u}.png",
                        f"Arc_{name_u}_Icon.png",
                        f"Arc_{name_u}.png",
                        f"{name_u}_Icon.png",
                        f"{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"Weapon_{name_u}_Art.png",
                        f"Weapon_{name_u}.png",
                        f"Arc_{name_u}.png",
                        f"{name_u}.png",
                    ])

            else:
                candidates["icon"].extend([
                    f"{name_u}_Icon.png",
                    f"{name_u}.png",
                ])
                candidates["wish"].extend([
                    f"{name_u}_Splash_Art.png",
                    f"{name_u}_Wish.png",
                ])

        # Deduplicate candidate lists
        candidates["icon"] = list(dict.fromkeys(candidates["icon"]))
        candidates["wish"] = list(dict.fromkeys(candidates["wish"]))
        return candidates

    def query_fandom_batch(self, wiki_subdomain: str, filenames: list[str]) -> dict[str, str]:
        """Query MediaWiki API for a batch of filenames and return a mapping of filename -> direct URL."""
        if not filenames:
            return {}

        results: dict[str, str] = {}
        chunk_size = 40  # MediaWiki limit per request is usually 50

        for i in range(0, len(filenames), chunk_size):
            chunk = filenames[i : i + chunk_size]
            titles_param = "|".join([f"File:{f}" if not f.startswith("File:") else f for f in chunk])
            api_url = f"https://{wiki_subdomain}.fandom.com/api.php"
            params = {
                "action": "query",
                "titles": titles_param,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            }

            try:
                resp = self.session.get(api_url, params=params, timeout=12)
                if resp.status_code != 200:
                    logger.warning(f"Fandom API returned status {resp.status_code} for {wiki_subdomain}")
                    continue

                data = resp.json()
                pages = data.get("query", {}).get("pages", {})

                for _, page_info in pages.items():
                    if "imageinfo" in page_info and page_info["imageinfo"]:
                        title = page_info.get("title", "")
                        clean_title = title.replace("File:", "").strip()
                        url = page_info["imageinfo"][0].get("url")
                        if url:
                            results[clean_title] = url
                            # Also map underscore variant
                            results[clean_title.replace(" ", "_")] = url
            except Exception as e:
                logger.error(f"Error querying Fandom API for {wiki_subdomain}: {e}", exc_info=True)

        return results

    async def download_images_async(
        self,
        download_tasks: list[tuple[str, Path]],
        max_concurrency: int | None = None,
    ) -> dict[str, bool]:
        """
        Download multiple images concurrently using httpx.AsyncClient and a concurrency semaphore.
        """
        if not download_tasks:
            return {}

        concurrency = max_concurrency or self.max_concurrency
        semaphore = asyncio.Semaphore(concurrency)
        results: dict[str, bool] = {}

        # Deduplicate tasks by URL to prevent redundant parallel downloads of the same asset
        unique_tasks: dict[str, Path] = {}
        for url, path in download_tasks:
            if url and url not in unique_tasks:
                unique_tasks[url] = path

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
            async def _fetch_single(url: str, target_path: Path) -> None:
                if target_path.exists() and target_path.stat().st_size > 0:
                    results[url] = True
                    return

                target_path.parent.mkdir(parents=True, exist_ok=True)
                async with semaphore:
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200 and resp.content:
                            target_path.write_bytes(resp.content)
                            logger.info(f"Downloaded image to {target_path}")
                            results[url] = True
                        else:
                            logger.warning(f"Failed to download image {url} (status: {resp.status_code})")
                            results[url] = False
                    except Exception as exc:
                        logger.error(f"Error downloading image {url}: {exc}")
                        results[url] = False

            await asyncio.gather(*[_fetch_single(u, p) for u, p in unique_tasks.items()])

        return results

    def download_images_concurrently(
        self,
        download_tasks: list[tuple[str, Path]],
        max_concurrency: int | None = None,
    ) -> dict[str, bool]:
        """
        Safely execute concurrent image downloads synchronously or within an active event loop.
        """
        if not download_tasks:
            return {}

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run,
                    self.download_images_async(download_tasks, max_concurrency=max_concurrency),
                )
                return future.result()
        else:
            return asyncio.run(
                self.download_images_async(download_tasks, max_concurrency=max_concurrency)
            )

    def download_image(self, url: str, target_path: Path) -> bool:
        """Download single image from url and save to target_path if it doesn't already exist."""
        results = self.download_images_concurrently([(url, target_path)])
        return results.get(url, False)

    def enrich_rewards(
        self,
        game_name: str,
        rewards: list[Reward],
        banner_type: BannerType | None = None,
        download_locally: bool = False,
    ) -> None:
        """Batch-resolve image URLs for a list of rewards and attach them to reward.extra_data."""
        if not rewards:
            return

        wiki = self._get_wiki_subdomain(game_name)
        is_weapon_banner = banner_type in (BannerType.LIMITED_WEAPON, BannerType.STANDARD_WEAPON)

        # Collect candidate filenames for all rewards
        reward_candidates: list[tuple[Reward, dict[str, list[str]]]] = []
        all_candidate_filenames: set[str] = set()

        for reward in rewards:
            is_char = not is_weapon_banner
            candidates = self._generate_candidate_titles(game_name, reward.name, is_character=is_char)
            reward_candidates.append((reward, candidates))
            all_candidate_filenames.update(candidates["icon"])
            all_candidate_filenames.update(candidates["wish"])

        # Fetch all candidate URLs in batch
        found_urls = self.query_fandom_batch(wiki, list(all_candidate_filenames))

        # Assign best matches to reward.extra_data and queue downloads
        game_folder_slug = wiki.replace("-", "_")
        download_tasks: list[tuple[str, Path]] = []
        reward_icon_refs: list[tuple[Reward, str, str]] = []
        reward_wish_refs: list[tuple[Reward, str, str]] = []

        for reward, candidates in reward_candidates:
            if reward.extra_data is None:
                reward.extra_data = {}

            # Match Icon
            icon_url: str | None = None
            for icon_cand in candidates["icon"]:
                if icon_cand in found_urls:
                    icon_url = found_urls[icon_cand]
                    break
                elif icon_cand.replace("_", " ") in found_urls:
                    icon_url = found_urls[icon_cand.replace("_", " ")]
                    break

            # Match Wish / Splash Art
            wish_url: str | None = None
            for wish_cand in candidates["wish"]:
                if wish_cand in found_urls:
                    wish_url = found_urls[wish_cand]
                    break
                elif wish_cand.replace("_", " ") in found_urls:
                    wish_url = found_urls[wish_cand.replace("_", " ")]
                    break

            # If Fandom didn't find wish art, fallback to prydwen_art
            if not wish_url and reward.extra_data.get("prydwen_art"):
                wish_url = reward.extra_data["prydwen_art"]

            # If Fandom didn't find icon, fallback to prydwen_icon
            if not icon_url and reward.extra_data.get("prydwen_icon"):
                icon_url = reward.extra_data["prydwen_icon"]

            if icon_url:
                reward.extra_data["icon_url"] = icon_url
            if wish_url:
                reward.extra_data["wish_url"] = wish_url

            # Prepare local download tasks
            if download_locally:
                safe_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", reward.name.lower().replace(" ", "_"))
                if icon_url:
                    ext = ".webp" if ".webp" in icon_url.lower() else ".png"
                    local_icon_path = self.cache_dir / game_folder_slug / f"{safe_name}_icon{ext}"
                    download_tasks.append((icon_url, local_icon_path))
                    reward_icon_refs.append(
                        (reward, icon_url, f"/static/images/{game_folder_slug}/{safe_name}_icon{ext}")
                    )

                if wish_url:
                    ext = ".webp" if ".webp" in wish_url.lower() else ".png"
                    local_wish_path = self.cache_dir / game_folder_slug / f"{safe_name}_wish{ext}"
                    download_tasks.append((wish_url, local_wish_path))
                    reward_wish_refs.append(
                        (reward, wish_url, f"/static/images/{game_folder_slug}/{safe_name}_wish{ext}")
                    )

        # Concurrently download all collected image assets in a single batch
        if download_locally and download_tasks:
            download_results = self.download_images_concurrently(download_tasks)

            for reward, icon_url, static_path in reward_icon_refs:
                if download_results.get(icon_url, False):
                    reward.extra_data["local_icon"] = static_path

            for reward, wish_url, static_path in reward_wish_refs:
                if download_results.get(wish_url, False):
                    reward.extra_data["local_wish"] = static_path

    def enrich_banners(
        self, banners: list[Banner], game_name: str, download_locally: bool = False
    ) -> list[Banner]:
        """Enrich all rewards across a list of banners with image URLs and local paths."""
        for banner in banners:
            all_rewards = banner.limited_rewards + banner.low_rate_rewards
            self.enrich_rewards(
                game_name=game_name,
                rewards=all_rewards,
                banner_type=banner.banner_type,
                download_locally=download_locally,
            )
        return banners
