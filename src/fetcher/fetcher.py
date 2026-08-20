import logging
import re
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from src.db.models import BannerType, Banner, Reward
from curl_cffi import requests
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT/ "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class BaseBannerFetcher(ABC):
    @abstractmethod
    def fetch_banners(self) -> list[Banner]:
        pass

class PrydwenBannerFetcher(BaseBannerFetcher):

    WEAPON_KEYWORDS: tuple[str, ...] = ()
    def __init__(self, url: str, game_name: str):
        self.url = url
        self.game_name = game_name
        
    def _get_html(self) -> str:
        try:
            response = requests.get(self.url, impersonate="chrome120", timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Received status code {response.status_code} for {self.url}")
                return ""
        except Exception as e:
            logger.error(f"Error fetching {self.url}: {e}", exc_info=True)
            return ""

    def _parse_patch_info(self, section: Tag) -> tuple[str | None, int | None]:
        h3_tag = section.find("h3")
        h3_text = h3_tag.get_text(strip=True) if h3_tag else ""
        h2_tag = section.find("h2")
        h2_text = h2_tag.get_text(strip=True) if h2_tag else ""
        section_id = section.get("id", "").lower()
        combined_header = f"{h3_text} {h2_text}"

        version_match = re.search(r"(?:Patch|Version|v)\s*(\d+\.(?:\d+|x|\?))", combined_header, re.IGNORECASE)
        phase_match = re.search(r"Phase\s*(\d+)", combined_header, re.IGNORECASE)

        if version_match:
            version = version_match.group(1).replace("?", "X").replace("x", "X")
            if phase_match:
                phase = int(phase_match.group(1))
            elif "phase ?" in combined_header.lower() or "phase x" in combined_header.lower() or "upcoming" in combined_header.lower() or "teased" in section_id:
                phase = 0
            elif "phase 2" in combined_header.lower() or "next" in combined_header.lower() or section_id == "next-banner":
                phase = 2
            elif "phase 1" in combined_header.lower() or "current" in combined_header.lower() or section_id == "current-banners":
                phase = 1
            else:
                phase = 1
            return (version, phase)
        elif phase_match:
            return ("0.0", int(phase_match.group(1)))
        elif "upcoming" in combined_header.lower() or "next" in combined_header.lower() or "teased" in section_id:
            return ("Upcoming", 0)
        else:
            return (None, None)

    def _parse_limited_rewards(self, banner: Tag) -> list[Reward]:
        name_tag = banner.find("p", class_="banner-name")
        char_name = name_tag.get_text(strip=True) if name_tag else "Featured Banner"

        # Capture banner artwork from Prydwen card as a direct fallback
        art_img = (
            banner.find("img", alt=re.compile(r"banner art", re.I))
            or banner.select_one(".banner-art img")
            or banner.find("img")
        )
        art_url = art_img.get("src") if art_img else None

        extra_data: dict[str, Any] = {}
        if art_url:
            extra_data["prydwen_art"] = art_url
            if "/characters/" in art_url:
                slug = art_url.split("/characters/")[-1].split(".")[0].replace("_full", "").replace("_image", "")
                slug_name = " ".join([p.capitalize() for p in slug.replace("_", "-").split("-") if p])
                if slug_name and slug_name.lower() != char_name.lower():
                    extra_data["character_alias"] = slug_name

        # Check for dual-weapon banner titles (e.g. Genshin Epitome Invocation: Weapon A & Weapon B)
        classes = banner.get("class", [])
        is_weapon_card = "weapon-banner-card" in classes or "light-cone-card" in classes
        name_lower = char_name.lower()

        if "epitome invocation" in name_lower or (is_weapon_card and (" & " in char_name or " and " in name_lower)):
            clean_str = re.sub(r"^Epitome Invocation\s*[:\-\(\[\{]?\s*", "", char_name, flags=re.IGNORECASE).strip("()[]{} ").strip()
            # Split by &, and, /, or comma
            weapon_parts = [w.strip() for w in re.split(r"\s*(?:&|and|/|,)\s*", clean_str) if w.strip()]
            if len(weapon_parts) > 1:
                return [
                    Reward(name=w, rarity=5, is_featured=True, extra_data=dict(extra_data))
                    for w in weapon_parts
                ]
            elif clean_str:
                return [Reward(name=clean_str, rarity=5, is_featured=True, extra_data=extra_data)]

        return [Reward(name=char_name, rarity=5, is_featured=True, extra_data=extra_data)]

    def _parse_rate_up_rewards(self, banner: Tag) -> list[Reward]:
        four_stars_div = (
            banner.find("div", class_="featured-rate-ups")
            or banner.find("div", class_="banner-rate-up-icons")
            or banner.find("div", class_="featured-rate-up")
        )
        four_stars_rewards = []

        if four_stars_div:
            four_stars_chars_links = four_stars_div.find_all("a", class_="featured-rate-up")
            if four_stars_chars_links:
                for a in four_stars_chars_links:
                    char_name = a.get_text(strip=True)
                    img = a.find("img")
                    icon_url = img.get("src") if img else None
                    extra = {"prydwen_icon": icon_url} if icon_url else {}
                    if char_name:
                        four_stars_rewards.append(Reward(name=char_name, rarity=4, is_featured=False, extra_data=extra))
            else:
                for img in four_stars_div.find_all("img"):
                    alt = img.get("alt", "").strip()
                    src = img.get("src", "").strip()
                    if alt or src:
                        name = alt
                        if not name and "/characters/" in src:
                            slug = src.split("/characters/")[-1].split("_")[0].split(".")[0]
                            name = " ".join([part.capitalize() for part in slug.replace("_", "-").split("-") if part])
                        elif not name and ("/weapons/" in src or "/light-cones/" in src or "/w-engines/" in src):
                            slug = src.split("/")[-1].split("_")[0].split(".")[0]
                            name = " ".join([part.capitalize() for part in slug.replace("_", "-").split("-") if part])
                        if name:
                            four_stars_rewards.append(Reward(name=name, rarity=4, is_featured=False, extra_data={"prydwen_icon": src}))

        return four_stars_rewards

    def _parse_date_range(self, banner: Tag, phase: int | None = None) -> tuple[datetime | None, datetime | None]:
        range_tag = banner.find('strong', attrs={'data-banner-range': 'true'})
        if not range_tag:
            return (None, None)
        banner_date_range = range_tag.get_text(strip=True)
        date_formats = ["%b %d, %Y", "%b %d %Y", "%B %d, %Y", "%B %d %Y"]

        if banner_date_range.strip().lower() in ("tba", "tbd", "to be announced", "unknown", ""):
            return (None, None)

        def _parse_single_date(date_str: str) -> datetime | None:
            clean = date_str.strip()
            for fmt in date_formats:
                try:
                    return datetime.strptime(clean, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            return None

        if banner_date_range.lower().startswith("from "):
            date_str = banner_date_range.split("From ", 1)[1].strip()
            start_date = _parse_single_date(date_str)
            if start_date:
                if phase == 1:
                    start_date = start_date.replace(hour=6, minute=0, second=0)
                elif phase == 2:
                    start_date = start_date.replace(hour=18, minute=0, second=0)
            return (start_date, None)
        else:
            parts = [d.strip() for d in re.split(r"\s*[\u2013\u2014\u2010\u2212-]\s*|\s+to\s+", banner_date_range) if d.strip()]
            if len(parts) == 2:
                start_date = _parse_single_date(parts[0])
                end_date = _parse_single_date(parts[1])

                if start_date and end_date:
                    # Set accurate start and end hours based on banner phase lifecycle
                    if phase == 1:
                        # Phase 1 starts after maintenance (~06:00 UTC) and ends at 17:59:59 UTC
                        start_date = start_date.replace(hour=6, minute=0, second=0)
                        end_date = end_date.replace(hour=17, minute=59, second=59)
                    elif phase == 2:
                        # Phase 2 starts at 18:00:00 UTC and ends at 14:59:59 UTC (before patch maintenance)
                        start_date = start_date.replace(hour=18, minute=0, second=0)
                        end_date = end_date.replace(hour=14, minute=59, second=59)
                    else:
                        # Default: active through end of day
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                    return (start_date, end_date)
            
            logger.warning(f"Unrecognized date range format: {banner_date_range}")
            return (None, None)

    def _determine_banner_type(self, banner: Tag) -> BannerType:
        classes = banner.get("class", [])
        if "weapon-banner-card" in classes or "light-cone-card" in classes:
            return BannerType.LIMITED_WEAPON
        elif "character-banner-card" in classes:
            return BannerType.LIMITED_CHARACTER
        
        # Fallback: check banner name against weapon keywords
        name_tag = banner.find("p", class_="banner-name")
        banner_text = name_tag.get_text(strip=True).lower() if name_tag else ""
        if self.WEAPON_KEYWORDS and any(keyword in banner_text for keyword in self.WEAPON_KEYWORDS):
            return BannerType.LIMITED_WEAPON

        logger.warning(f"Could not determine banner type for banner card '{banner_text}', defaulting to LIMITED_CHARACTER")
        return BannerType.LIMITED_CHARACTER
        
            
    def fetch_banners(self) -> list[Banner]:
        html = self._get_html()
        soup = BeautifulSoup(html, "html.parser")
        banners_list: list[Banner] = []
        sections = soup.find_all("section", class_="section-group")

        latest_known_end_date: datetime | None = None

        # First pass: parse sections and extract known dated banners while finding latest known end date
        for section in sections:
            version, phase = self._parse_patch_info(section)
            if version is None:
                continue
            banners = section.find_all("article", class_="banner-card")
    
            for banner in banners:
                limited_rewards = self._parse_limited_rewards(banner)
                four_stars_rewards = self._parse_rate_up_rewards(banner)
                start_date, end_date = self._parse_date_range(banner, phase=phase)

                # Track latest known end date for future TBA calculation
                if end_date and (latest_known_end_date is None or end_date > latest_known_end_date):
                    latest_known_end_date = end_date

                # If date range is TBA or unknown, estimate upcoming start date
                if start_date is None:
                    fallback_start = (
                        (latest_known_end_date + timedelta(days=1))
                        if latest_known_end_date
                        else (datetime.now(timezone.utc) + timedelta(days=21))
                    )
                    start_date = fallback_start.replace(hour=6, minute=0, second=0)
                    end_date = None
                    for r in limited_rewards:
                        if r.extra_data is None:
                            r.extra_data = {}
                        r.extra_data["date_tba"] = True
                        r.extra_data["schedule"] = "TBA"

                banner_type = self._determine_banner_type(banner)                     
                banners_list.append(
                    Banner(version, banner_type, limited_rewards, four_stars_rewards, start_date, end_date, phase or 0)
                )

        return banners_list

class GenshinBannerFetcher(PrydwenBannerFetcher):
    WEAPON_KEYWORDS = ("weapon", "epitome")

class StarrailBannerFetcher(PrydwenBannerFetcher):
    WEAPON_KEYWORDS = ("light cone", "brilliant fixation", "bygone reminiscence")

class WutheringWavesFetcher(PrydwenBannerFetcher):
    WEAPON_KEYWORDS = ("weapon", "absolute pulsar")

class ZenlessZoneZeroFetcher(PrydwenBannerFetcher):
    WEAPON_KEYWORDS = ("w-engine", "engine", "bangboo", "weapon", "d-engine", "channel")

class NevernessToEvernessFetcher(PrydwenBannerFetcher):
    WEAPON_KEYWORDS = ("weapon", "blade", "light cone", "equipment", "arc", "convene")



             

            


        