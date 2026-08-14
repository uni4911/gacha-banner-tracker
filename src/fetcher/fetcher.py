import logging
import re
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from src.models.models import BannerType, Banner, Reward
from curl_cffi import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
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
                logger.error(f"Otrzymano status {response.status_code} dla {self.url}")
                return ""
        except Exception as e:
            logger.error(f"Błąd podczas pobierania {self.url}: {e}", exc_info=True)
            return ""

    def _parse_patch_info(self, section: Tag) -> tuple[str | None, int | None]:
        h3_tag = section.find("h3")

        if not h3_tag or "Patch" not in h3_tag.text:
            return (None, None)

        version_phase_text = section.find("h3").text

        version_pattern = r"Patch\s+(\d+\.\d+)"
        version_match = re.search(version_pattern, version_phase_text)

        phase_pattern = r"Phase\s+(\d+)"
        phase_match = re.search(phase_pattern, version_phase_text)

        if version_match and phase_match:
            version = version_match.group(1)
            phase = int(phase_match.group(1))
        else:
            version = "0.0"
            phase = 1

        return (version, phase)


    def _parse_limited_rewards(self, banner: Tag) -> list[Reward]:
        limited_character_name = [banner.find("p",class_="banner-name").get_text(strip=True)]
        limited_rewards = [Reward(name=char_name, rarity=5, is_featured=True) for char_name in limited_character_name]
        return limited_rewards

    def _parse_rate_up_rewards(self, banner: Tag) -> list[Reward]:
        four_stars_div = banner.find("div",class_="featured-rate-ups")
        four_stars_rewards = []

        if four_stars_div:
            four_stars_chars_links = four_stars_div.find_all("a",class_="featured-rate-up")
            four_stars_chars_names = [a.get_text(strip=True) for a in four_stars_chars_links]
            four_stars_rewards = [Reward(name=char_name, rarity=4, is_featured=False) for char_name in four_stars_chars_names]
        return four_stars_rewards

    def _parse_date_range(self, banner: Tag) -> tuple[datetime | None, datetime | None]:

        banner_date_range = banner.find('strong', attrs={'data-banner-range': 'true'}).get_text(strip=True)
        date_format = "%b %d, %Y"

        if banner_date_range.lower().startswith("from "):
            date_str = banner_date_range.split("From ", 1)[1].strip()
            start_date = datetime.strptime(date_str, date_format).replace(tzinfo=timezone.utc)
            end_date = None 
        else:
            parts = [d.strip() for d in re.split(r"\s*[\u2013\u2014\u2010\u2212-]\s*", banner_date_range) if d.strip()]
            if len(parts) == 2:
                start_date = datetime.strptime(parts[0], date_format).replace(tzinfo=timezone.utc)
                end_date = datetime.strptime(parts[1], date_format).replace(tzinfo=timezone.utc)
            else:
                logger.warning(f"Nie rozpoznano formatu daty: {banner_date_range}")
                return (None, None)
                
        return (start_date, end_date)

    def _determine_banner_type(self, banner: Tag) -> BannerType:
        tag = banner.find("span", class_="rarity")
        if not tag:
            return BannerType.LIMITED_CHARACTER

        banner_type = tag.get_text(strip=True).lower(   )
        for keyword in self.WEAPON_KEYWORDS:
            if keyword in banner_type:
                return BannerType.LIMITED_WEAPON
        return BannerType.LIMITED_CHARACTER
        
            
    def fetch_banners(self) -> list[Banner]:
        html = self._get_html()
        soup = BeautifulSoup(html, "html.parser")
        banners_list = []
        sections = soup.find_all("section",class_="section-group")

        for section in sections:
            version, phase = self._parse_patch_info(section)
            if version is None:
                continue
            banners = section.find_all("article",class_="banner-card")
            

            for banner in banners:
                limited_rewards = self._parse_limited_rewards(banner)
                four_stars_rewards = self._parse_rate_up_rewards(banner)
                start_date, end_date = self._parse_date_range(banner)

                if start_date is None:
                    continue
                banner_type = self._determine_banner_type(banner)                     

                banners_list.append(Banner(version,banner_type,limited_rewards,four_stars_rewards,start_date,end_date,phase))

        return banners_list

class GenshinBannerFetcher(PrydwenBannerFetcher):
    WEAPON_KEYWORDS = ("weapon",)

class StarrailBannerFetcher(PrydwenBannerFetcher):
    WEAPON_KEYWORDS = ("light cone",)


             

            


        