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


KNOWN_CHARACTER_ALIASES: dict[str, list[str]] = {
    "lucy": ["Luciana de Montefio", "Luciana Auxesis Theodoro de Montefio", "Lucy"],
    "harumasa": ["Asaba Harumasa", "Harumasa"],
    "yuzuha": ["Ukinami Yuzuha", "Yuzuha"],
    "sigrid": ["Sigrid de L'Azur", "Sigrid"],
    "remielle": ["Remielle Dan Seashade Pas Seul", "Remielle Dan Moonlight Whispers", "Remielle"],
    "claret": ["Claret Flint", "Claret"],
    "roxy": ["Roxy Ifrita Pryce", "Roxy"],
    "ellen": ["Ellen Joe", "Ellen"],
    "miyabi": ["Hoshimi Miyabi", "Miyabi"],
    "yanagi": ["Tsukishiro Yanagi", "Yanagi"],
    "piper": ["Piper Wheel", "Piper"],
    "corin": ["Corin Wickes", "Corin"],
    "billy": ["Billy Kid", "Billy"],
    "anby": ["Anby Demara", "Anby"],
    "nicole": ["Nicole Demara", "Nicole"],
    "nekomata": ["Nekomiya Mana", "Nekomata"],
    "grace": ["Grace Howard", "Grace"],
    "anton": ["Anton Ivanov", "Anton"],
    "koleda": ["Koleda Belobog", "Koleda"],
    "ben": ["Ben Bigger", "Ben"],
    "rina": ["Alexandrina Sebastiane", "Rina"],
    "lycaon": ["Von Lycaon", "Lycaon"],
    "seth": ["Seth Lowell", "Seth"],
    "jane": ["Jane Doe", "Jane"],
    "caesar": ["Caesar King", "Caesar"],
    "burnice": ["Burnice White", "Burnice"],
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

    def _get_name_variations(self, name: str, extra_aliases: list[str] | None = None) -> list[str]:
        """Generate common spelling/alias variations for a character or weapon name."""
        cleaned = re.sub(r"\s+", " ", name.strip())
        variations = [cleaned]

        if extra_aliases:
            for ea in extra_aliases:
                ea_clean = re.sub(r"\s+", " ", ea.strip())
                if ea_clean and ea_clean not in variations:
                    variations.append(ea_clean)

        # Look up known aliases
        name_lower = cleaned.lower()
        if name_lower in KNOWN_CHARACTER_ALIASES:
            for a in KNOWN_CHARACTER_ALIASES[name_lower]:
                if a not in variations:
                    variations.append(a)
        else:
            for k, aliases in KNOWN_CHARACTER_ALIASES.items():
                if k in name_lower or name_lower in k:
                    for a in aliases:
                        if a not in variations:
                            variations.append(a)

        # Handle bullet separation (e.g. Himeko Nova -> Himeko • Nova)
        parts = cleaned.split()
        if len(parts) == 2 and "•" not in cleaned:
            variations.append(f"{parts[0]} • {parts[1]}")
            variations.append(parts[0])  # Base / First name fallback (e.g. Himeko, Ellen, Asaba)
            variations.append(parts[1])  # Last name / Given name fallback (e.g. Harumasa, Miyabi, Yanagi, Joe)
        elif len(parts) >= 3 and "•" not in cleaned:
            variations.append(f"{parts[0]} • {' '.join(parts[1:])}")
            variations.append(f"{' '.join(parts[:2])} • {' '.join(parts[2:])}")
            variations.append(" ".join(parts[:2]))
            variations.append(" ".join(parts[1:]))
            variations.append(parts[0])
            variations.append(parts[-1])

        if "•" in cleaned:
            variations.append(cleaned.replace("•", " ").replace("  ", " ").strip())
            variations.append(cleaned.split("•")[0].strip())
            variations.append(cleaned.split("•")[-1].strip())

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
        self, game_name: str, item_name: str, is_character: bool = True, extra_aliases: list[str] | None = None
    ) -> dict[str, list[str]]:
        """Generate candidate wiki filenames prioritizing transparent full-body splash art without background."""
        wiki = self._get_wiki_subdomain(game_name)
        candidates: dict[str, list[str]] = {"icon": [], "wish": []}
        name_variants = self._get_name_variations(item_name, extra_aliases=extra_aliases)

        for name in name_variants:
            name_u = name.replace(" ", "_")

            if "genshin" in wiki:
                if is_character:
                    candidates["icon"].extend([
                        f"{name_u}_Icon.png",
                        f"{name_u}_Side_Icon.png",
                        f"Character_{name_u}_Icon.png",
                        f"{name_u}_Item.png",
                        f"{name_u}.png",
                    ])
                    # Strictly prioritize official transparent full-body Splash Art / Full Wish cutouts without background
                    candidates["wish"].extend([
                        f"Character_{name_u}_Full_Wish.png",
                        f"{name_u}_Portrait.png",
                        f"Character_{name_u}_Game.png",
                        f"Character_{name_u}_Splash_Art.png",
                        f"{name_u}_Splash_Art.png",
                        f"Character_{name_u}_Full.png",
                        f"{name_u}_Full.png",
                        f"Character_{name_u}_Card.png",
                        f"{name_u}_Card.png",
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
                        f"Character_{name_u}_Avatar.png",
                        f"{name_u}_Avatar.png",
                        f"Character_{name_u}.png",
                        f"{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"Character_{name_u}_Splash_Art.png",
                        f"{name_u}_Splash_Art.png",
                        f"Character_{name_u}_Full.png",
                        f"{name_u}_Full.png",
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
                        f"Resonator_{name_u}_Icon.png",
                        f"{name_u}Card.png",
                        f"{name_u}_Card.png",
                        f"{name_u}.png",
                    ])
                    # Strictly prioritize official transparent full-body sprite / splash art without background
                    candidates["wish"].extend([
                        f"Resonator_{name_u}_Full_Sprite.png",
                        f"{name_u}_Full_Sprite.png",
                        f"Resonator_{name_u}_Splash_Art.png",
                        f"{name_u}_Splash_Art.png",
                        f"Resonator_{name_u}_Full.png",
                        f"{name_u}_Full.png",
                        f"Resonator_{name_u}.png",
                        f"{name_u}.png",
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
                        f"{name_u}_Icon.png",
                        f"Agent_{name_u}_Portrait.png",
                        f"Agent_{name_u}_Avatar.png",
                        f"Agent_{name_u}.png",
                        f"Bangboo_{name_u}_Icon.png",
                        f"Bangboo_{name_u}.png",
                        f"Character_{name_u}_Icon.png",
                        f"{name_u}.png",
                    ])
                    # Strictly prioritize official full transparent Agent Portrait (as displayed on Fandom Media)
                    candidates["wish"].extend([
                        f"Agent_{name_u}_Portrait.png",
                        f"Agent_{name_u}_Human_Portrait.png",
                        f"{name_u}_Portrait.png",
                        f"Agent_{name_u}_Full_Portrait.png",
                        f"Agent_{name_u}_In-Game.png",
                        f"Agent_{name_u}_In_Game.png",
                        f"Agent_{name_u}_Splash_Art.png",
                        f"{name_u}_Splash_Art.png",
                        f"Character_{name_u}_Splash_Art.png",
                        f"Agent_{name_u}_Full.png",
                        f"{name_u}_Full.png",
                        f"Bangboo_{name_u}_Portrait.png",
                        f"Bangboo_{name_u}_Splash_Art.png",
                        f"Bangboo_{name_u}_Full.png",
                        f"Agent_{name_u}.png",
                        f"{name_u}.png",
                    ])
                else:
                    candidates["icon"].extend([
                        f"W-Engine_{name_u}_Icon.png",
                        f"W-Engine_{name_u}.png",
                        f"W_Engine_{name_u}.png",
                        f"Item_{name_u}_Icon.png",
                        f"Item_{name_u}.png",
                        f"{name_u}_Icon.png",
                        f"{name_u}.png",
                    ])
                    candidates["wish"].extend([
                        f"W-Engine_{name_u}_Art.png",
                        f"W-Engine_{name_u}_Splash_Art.png",
                        f"W-Engine_{name_u}.png",
                        f"W_Engine_{name_u}_Art.png",
                        f"W_Engine_{name_u}.png",
                        f"{name_u}_Art.png",
                        f"{name_u}_Splash_Art.png",
                        f"{name_u}.png",
                    ])

            elif "neverness" in wiki:
                if is_character:
                    candidates["icon"].extend([
                        f"Esper_{name_u}_Icon.png",
                        f"Character_{name_u}_Icon.png",
                        f"{name_u}_Icon.png",
                        f"Esper_{name_u}_Avatar.png",
                        f"Esper_{name_u}_Portrait.png",
                        f"Esper_{name_u}.png",
                        f"Agent_{name_u}_Icon.png",
                        f"Character_{name_u}.png",
                        f"{name_u}.png",
                    ])
                    # Strictly prioritize high-resolution full body Portrait art (e.g. Nanally_Portrait.png, Mint_Portrait.png)
                    candidates["wish"].extend([
                        f"{name_u}_Portrait.png",
                        f"Esper_{name_u}_Portrait.png",
                        f"Character_{name_u}_Portrait.png",
                        f"Esper_{name_u}_Full_Artwork.png",
                        f"{name_u}_Full_Artwork.png",
                        f"Esper_{name_u}_Artwork.png",
                        f"{name_u}_Artwork.png",
                        f"Esper_{name_u}_Splash_Art.png",
                        f"{name_u}_Splash_Art.png",
                        f"Character_{name_u}_Splash_Art.png",
                        f"Esper_{name_u}_Full.png",
                        f"Esper_{name_u}_Full_Sprite.png",
                        f"Character_{name_u}_Full.png",
                        f"{name_u}_Full.png",
                        f"Esper_{name_u}.png",
                        f"Character_{name_u}.png",
                        f"{name_u}.png",
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
                        f"Weapon_{name_u}_Splash_Art.png",
                        f"Weapon_{name_u}_Art.png",
                        f"Weapon_{name_u}.png",
                        f"Arc_{name_u}_Art.png",
                        f"Arc_{name_u}_Splash_Art.png",
                        f"Arc_{name_u}.png",
                        f"{name_u}_Art.png",
                        f"{name_u}_Splash_Art.png",
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

    def _search_fandom_files_dynamic(self, wiki_subdomain: str, query: str) -> list[str]:
        """Search MediaWiki API dynamically for image files matching a character/weapon query."""
        url = f"https://{wiki_subdomain}.fandom.com/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srnamespace": 6,  # File namespace
            "srsearch": query,
            "srlimit": 25,
            "format": "json",
        }
        try:
            r = self.session.get(url, params=params, timeout=10).json()
            pages = r.get("query", {}).get("search", [])
            return [p["title"].replace("File:", "").strip() for p in pages if "title" in p]
        except Exception as e:
            logger.debug(f"Dynamic MediaWiki search error for {query} on {wiki_subdomain}: {e}")
            return []

    def _rank_dynamic_files(
        self, filenames: list[str], game_name: str, is_character: bool = True
    ) -> dict[str, list[str]]:
        """Rank and categorize search hits from MediaWiki into prioritized transparent icon and wish candidates."""
        wiki = self._get_wiki_subdomain(game_name)
        icons: list[tuple[str, str]] = []
        wishes: list[tuple[str, str]] = []

        promo_exclude = [
            ".ogg", ".mp3", ".mp4", ".gif",
            "agent_record", "agent record",
            "drip_marketing", "drip marketing",
            "convene_draw", "convene draw",
            "convene_still", "convene still",
            "teaser", "reveal", "announcement",
            "birthday", "shorts", "voice actor", "voice_actor",
            "tutorial", "trailer", "showcase",
            "wallpaper", "sheet", "expression",
            "sticker", "hangout", "slice of life", "slice_of_life",
            "character details", "character_details",
            "character notes", "character_notes",
            "talent demo", "combat intel", "item agent focus",
            "multi wish", "multi_wish",
        ]

        if "zenless" in wiki:
            wish_keywords = ["portrait", "human_portrait", "full_portrait", "in-game", "in_game", "splash_art", "full"]
        elif "neverness" in wiki:
            wish_keywords = ["portrait", "full_artwork", "artwork", "splash_art", "splash", "full"]
        elif "wuthering" in wiki:
            wish_keywords = ["full_sprite", "splash_art", "splash", "full"]
        elif "genshin" in wiki:
            wish_keywords = ["full_wish", "portrait", "game", "splash_art", "splash", "full"]
        else:
            wish_keywords = ["splash_art", "splash", "full_wish", "full_sprite", "portrait", "full"]

        icon_keywords = ["circle_icon", "icon", "avatar", "item", "weapon", "light_cone", "w-engine", "w_engine", "card"]

        for f in filenames:
            f_lower = f.lower()
            if any(pe in f_lower for pe in promo_exclude):
                continue

            for kw in wish_keywords:
                if kw in f_lower.replace(" ", "_"):
                    if f not in [item[1] for item in wishes]:
                        wishes.append((kw, f))
                    break

            for kw in icon_keywords:
                if kw in f_lower.replace(" ", "_"):
                    if f not in [item[1] for item in icons]:
                        icons.append((kw, f))
                    break

        sorted_wishes = [f for _, f in sorted(wishes, key=lambda x: wish_keywords.index(x[0]))]
        sorted_icons = [f for _, f in sorted(icons, key=lambda x: icon_keywords.index(x[0]))]
        return {"icon": sorted_icons, "wish": sorted_wishes}

    def query_fandom_batch(self, wiki_subdomain: str, filenames: list[str]) -> dict[str, str]:
        """Query MediaWiki API for a batch of filenames and return a mapping of filename -> direct URL."""
        if not filenames:
            return {}

        results: dict[str, str] = {}
        # MediaWiki API allows max 50 titles per request
        batch_size = 50

        for i in range(0, len(filenames), batch_size):
            chunk = filenames[i : i + batch_size]
            titles_param = "|".join([f"File:{f.replace(' ', '_')}" for f in chunk])
            api_url = f"https://{wiki_subdomain}.fandom.com/api.php"
            params = {
                "action": "query",
                "titles": titles_param,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            }

            try:
                response = self.session.get(api_url, params=params, timeout=10)
                if response.status_code != 200:
                    logger.warning(
                        f"Fandom API query failed with status {response.status_code} for {wiki_subdomain}"
                    )
                    continue

                data = response.json()
                pages = data.get("query", {}).get("pages", {})

                for page_id, page_data in pages.items():
                    if "imageinfo" in page_data and page_data["imageinfo"]:
                        url = page_data["imageinfo"][0]["url"]
                        raw_title = page_data.get("title", "")
                        clean_title = raw_title.replace("File:", "").strip()
                        if clean_title:
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
        overwrite: bool = True,
    ) -> dict[str, bool]:
        """
        Download multiple images asynchronously with bounded concurrency.
        Returns a mapping of url -> success_bool.
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
                if not overwrite and target_path.exists() and target_path.stat().st_size > 0:
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
        overwrite: bool = True,
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
                    self.download_images_async(download_tasks, max_concurrency=max_concurrency, overwrite=overwrite),
                )
                return future.result()
        else:
            return asyncio.run(
                self.download_images_async(download_tasks, max_concurrency=max_concurrency, overwrite=overwrite)
            )

    def download_image(self, url: str, target_path: Path, overwrite: bool = True) -> bool:
        """Download single image from url and save to target_path."""
        results = self.download_images_concurrently([(url, target_path)], overwrite=overwrite)
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

        # Filter rewards that still need icon or wish art resolution
        rewards_to_query: list[Reward] = []
        for reward in rewards:
            if reward.extra_data is None:
                reward.extra_data = {}
            has_icon = bool(reward.extra_data.get("icon_url") or reward.extra_data.get("local_icon"))
            has_wish = bool(reward.extra_data.get("wish_url") or reward.extra_data.get("local_wish"))
            if not (has_icon and has_wish):
                rewards_to_query.append(reward)

        # 1. Collect candidate filenames from naming patterns
        reward_candidates: list[tuple[Reward, dict[str, list[str]]]] = []
        all_candidate_filenames: set[str] = set()

        for reward in rewards_to_query:
            is_char = not is_weapon_banner
            alias = reward.extra_data.get("character_alias") if reward.extra_data else None
            extra_aliases = [alias] if alias else None
            candidates = self._generate_candidate_titles(
                game_name, reward.name, is_character=is_char, extra_aliases=extra_aliases
            )
            reward_candidates.append((reward, candidates))
            if not (reward.extra_data.get("icon_url") or reward.extra_data.get("local_icon")):
                all_candidate_filenames.update(candidates["icon"])
            if not (reward.extra_data.get("wish_url") or reward.extra_data.get("local_wish")):
                all_candidate_filenames.update(candidates["wish"])

        # Fetch candidate URLs in batch
        found_urls = self.query_fandom_batch(wiki, list(all_candidate_filenames)) if all_candidate_filenames else {}

        # 2. Dynamic discovery fallback for any rewards that didn't hit pattern candidates
        dynamic_unresolved_candidates: list[tuple[Reward, dict[str, list[str]]]] = []
        dynamic_filenames: set[str] = set()

        for reward, candidates in reward_candidates:
            has_matched_icon = any(c in found_urls or c.replace("_", " ") in found_urls for c in candidates["icon"])
            has_matched_wish = any(c in found_urls or c.replace("_", " ") in found_urls for c in candidates["wish"])

            if not (has_matched_icon and has_matched_wish):
                is_char = not is_weapon_banner
                discovered_files = self._search_fandom_files_dynamic(wiki, reward.name)
                alias = reward.extra_data.get("character_alias") if reward.extra_data else None
                if alias and alias.lower() != reward.name.lower():
                    discovered_files.extend(self._search_fandom_files_dynamic(wiki, alias))
                if discovered_files:
                    ranked = self._rank_dynamic_files(discovered_files, game_name, is_character=is_char)
                    dynamic_unresolved_candidates.append((reward, ranked))
                    dynamic_filenames.update(ranked["icon"])
                    dynamic_filenames.update(ranked["wish"])

        if dynamic_filenames:
            dynamic_urls = self.query_fandom_batch(wiki, list(dynamic_filenames))
            found_urls.update(dynamic_urls)

        # 3. Assign best matches to reward.extra_data and queue downloads
        game_folder_slug = wiki.replace("-", "_")
        download_tasks: list[tuple[str, Path]] = []
        reward_icon_refs: list[tuple[Reward, str, str]] = []
        reward_wish_refs: list[tuple[Reward, str, str]] = []

        # Merge dynamic candidates into main candidate list for each reward
        dynamic_map = {r: c for r, c in dynamic_unresolved_candidates}

        for reward, candidates in reward_candidates:
            if reward.extra_data is None:
                reward.extra_data = {}

            all_icon_cands = candidates["icon"] + dynamic_map.get(reward, {}).get("icon", [])
            all_wish_cands = candidates["wish"] + dynamic_map.get(reward, {}).get("wish", [])

            # Match Icon
            icon_url: str | None = None
            for icon_cand in all_icon_cands:
                if icon_cand in found_urls:
                    icon_url = found_urls[icon_cand]
                    break
                elif icon_cand.replace("_", " ") in found_urls:
                    icon_url = found_urls[icon_cand.replace("_", " ")]
                    break

            # Match Wish / Splash Art
            wish_url: str | None = None
            for wish_cand in all_wish_cands:
                if wish_cand in found_urls:
                    wish_url = found_urls[wish_cand]
                    break
                elif wish_cand.replace("_", " ") in found_urls:
                    wish_url = found_urls[wish_cand.replace("_", " ")]
                    break

            # If Fandom didn't find wish art, fallback to prydwen_art or prydwen_icon
            if not wish_url and reward.extra_data.get("prydwen_art"):
                wish_url = reward.extra_data["prydwen_art"]

            # If Fandom didn't find icon, fallback to prydwen_icon or prydwen_art
            if not icon_url and reward.extra_data.get("prydwen_icon"):
                icon_url = reward.extra_data["prydwen_icon"]

            # Cross-fallback: if icon is still missing, fallback to wish_url or prydwen_art
            if not icon_url and wish_url:
                icon_url = wish_url
            elif not icon_url and reward.extra_data.get("prydwen_art"):
                icon_url = reward.extra_data["prydwen_art"]

            # Cross-fallback: if wish is still missing, fallback to icon_url or prydwen_icon
            if not wish_url and icon_url:
                wish_url = icon_url
            elif not wish_url and reward.extra_data.get("prydwen_icon"):
                wish_url = reward.extra_data["prydwen_icon"]

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
