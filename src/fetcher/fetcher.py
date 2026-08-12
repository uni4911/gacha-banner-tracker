import httpx
import logging
import re
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path
from bs4 import BeautifulSoup
from src.models.models import BannerType, Banner
from curl_cffi import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT/ "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

GENSHIN_URL = "https://www.prydwen.gg/genshin-impact/banners"

class BaseBannerFetcher(ABC):
    @abstractmethod
    def fetch_banners(self) -> list[Banner]:
        pass

class GenshinBannerFetcher(BaseBannerFetcher):

    def _get_html(self, url: str) -> str:
        try:
            response = requests.get(url, impersonate="chrome120", timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Otrzymano status {response.status_code} dla {url}")
                return ""
        except Exception as e:
            logger.error(f"Błąd podczas pobierania {url}: {e}", exc_info=True)
            return ""
            
    def fetch_banners(self) -> list[Banner]:
        html = self._get_html(GENSHIN_URL)
        soup = BeautifulSoup(html, "html.parser")
        banners_list = []
        sections = soup.find_all("section",class_="section-group")

        for section in sections:
            
            h3_tag = section.find("h3")
            if not h3_tag or "Patch" not in h3_tag.text:
                continue
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


            banners = section.find_all("article",class_="banner-card")

            for banner in banners:
                limited_character_name = [banner.find("p",class_="banner-name").get_text(strip=True)]

                four_stars_div = banner.find("div",class_="featured-rate-ups")
                four_stars_chars_names = []
                if four_stars_div:
                    four_stars_chars_links = four_stars_div.find_all("a",class_="featured-rate-up")
                    four_stars_chars_names = [a.get_text(strip=True) for a in four_stars_chars_links]

                banner_date_range = banner.find('strong', attrs={'data-banner-range': 'true'}).get_text(strip=True)
                start_str, end_str = [d.strip() for d in re.split(r"\s*[\u2013\u2014-]\s*",banner_date_range)]

                date_format = "%b %d, %Y"
                start_date = datetime.strptime(start_str, date_format)
                end_date = datetime.strptime(end_str, date_format)

                banners_list.append(Banner(version,BannerType.LIMITED_CHARACTER,limited_character_name,four_stars_chars_names,start_date,end_date,phase))

        return banners_list


             

            


        