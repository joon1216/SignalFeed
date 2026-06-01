"""
Pexels API 이미지 검색 및 다운로드
Instagram 카드 배경 이미지 자동 수집
"""

import os
import requests
from PIL import Image
from io import BytesIO
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ImageFetcher:
    """Pexels API로 키워드 기반 이미지 검색 및 다운로드"""

    PEXELS_API_URL = "https://api.pexels.com/v1/search"

    # 경제 뉴스 키워드 → Pexels 검색어 매핑
    KEYWORD_MAPPING = {
        # 금리/통화정책
        "federal reserve": "federal reserve building washington",
        "interest rate": "federal reserve building",
        "fed": "federal reserve building washington",
        "fomc": "federal reserve meeting",

        # 인플레이션/물가
        "inflation": "money inflation economy graph",
        "cpi": "consumer price inflation chart",
        "price": "inflation economy finance",

        # 기술주
        "nvidia": "semiconductor chip technology nvidia",
        "apple": "apple technology innovation",
        "microsoft": "microsoft technology cloud",
        "tesla": "tesla electric vehicle innovation",
        "semiconductor": "semiconductor chip technology",
        "chip": "microchip semiconductor technology",

        # 에너지
        "oil": "oil energy industry petroleum",
        "energy": "renewable energy industry",
        "opec": "oil petroleum industry",

        # 경제지표
        "recession": "economy business finance downturn",
        "gdp": "economy growth business finance",
        "employment": "job employment business office",
        "unemployment": "unemployment job search economy",

        # 주식시장
        "stock": "stock market trading finance",
        "s&p 500": "stock market wall street",
        "nasdaq": "technology stock market trading",
        "dow jones": "stock market wall street nyse",

        # 무역/관세
        "tariff": "international trade cargo port",
        "trade war": "international trade shipping",
        "export": "cargo ship international trade",

        # 금융
        "dollar": "us dollar currency finance",
        "treasury": "us treasury bonds finance",
        "bond": "bonds finance investment",

        # Default
        "default": "global economy finance business"
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ImageFetcher

        Args:
            api_key: Pexels API key (defaults to PEXELS_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("PEXELS_API_KEY")
        if not self.api_key:
            logger.warning("PEXELS_API_KEY not found, will use fallback backgrounds")

    def fetch(self, keyword: str, orientation: str = "square") -> Optional[Image.Image]:
        """
        Pexels API로 이미지 검색 및 다운로드

        Args:
            keyword: 검색 키워드
            orientation: 이미지 방향 (square/landscape/portrait)

        Returns:
            PIL Image object (1080x1080px) or None if failed
        """
        if not self.api_key:
            logger.warning("No API key, returning None")
            return None

        try:
            headers = {"Authorization": self.api_key}
            params = {
                "query": keyword,
                "per_page": 5,
                "orientation": orientation
            }

            response = requests.get(
                self.PEXELS_API_URL,
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            photos = data.get("photos", [])

            if not photos:
                logger.warning(f"No photos found for keyword: {keyword}")
                return None

            # Download first photo
            photo = photos[0]
            image_url = photo["src"]["large"]  # Use large size for quality

            img_response = requests.get(image_url, timeout=10)
            img_response.raise_for_status()

            # Open and resize to 1080x1080
            image = Image.open(BytesIO(img_response.content))
            image = image.resize((1080, 1080), Image.Resampling.LANCZOS)

            logger.info(f"✅ Fetched image for '{keyword}': {photo['photographer']}")
            return image

        except Exception as e:
            logger.error(f"Failed to fetch image for '{keyword}': {e}")
            return None

    def fetch_with_fallback(self, keywords: List[str]) -> Image.Image:
        """
        여러 키워드 시도 후 fallback 배경 반환

        Args:
            keywords: 검색 키워드 리스트 (우선순위 순)

        Returns:
            PIL Image object (1080x1080px), fallback if all fail
        """
        # Try each keyword
        for keyword in keywords:
            # Map to Pexels-friendly term
            mapped_keyword = self._map_keyword(keyword)
            image = self.fetch(mapped_keyword)
            if image:
                return image

        # All failed → return dark solid background
        logger.warning(f"All keywords failed, using fallback background")
        return self._create_fallback_background()

    def _map_keyword(self, keyword: str) -> str:
        """
        경제 뉴스 키워드를 Pexels 검색어로 변환

        Args:
            keyword: 원본 키워드

        Returns:
            Pexels 검색어
        """
        keyword_lower = keyword.lower()

        # Check exact matches first
        if keyword_lower in self.KEYWORD_MAPPING:
            return self.KEYWORD_MAPPING[keyword_lower]

        # Check partial matches
        for key, value in self.KEYWORD_MAPPING.items():
            if key in keyword_lower or keyword_lower in key:
                return value

        # Default fallback
        return self.KEYWORD_MAPPING["default"]

    def _create_fallback_background(self) -> Image.Image:
        """
        Fallback 배경 이미지 생성 (단색 dark bg)

        Returns:
            PIL Image object (1080x1080px, #1A1A1A)
        """
        image = Image.new("RGB", (1080, 1080), "#1A1A1A")
        return image

    def extract_keywords_from_cluster(self, cluster_data: dict) -> List[str]:
        """
        클러스터 데이터에서 Pexels 검색 키워드 추출

        Args:
            cluster_data: 클러스터 데이터 (cluster_label, articles)

        Returns:
            검색 키워드 리스트 (우선순위 순)
        """
        keywords = []

        # 1. cluster_label에서 추출
        cluster_label = cluster_data.get("cluster_label", "")
        if cluster_label and cluster_label != "노이즈":
            keywords.append(cluster_label)

        # 2. article titles에서 추출 (첫 3개)
        articles = cluster_data.get("articles", [])
        for article in articles[:3]:
            title = article.get("title", "")
            if title:
                # Extract potential keywords (capitalized words, economics terms)
                words = title.split()
                for word in words:
                    if word.lower() in self.KEYWORD_MAPPING:
                        keywords.append(word.lower())

        # 3. Default fallback
        if not keywords:
            keywords.append("default")

        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique_keywords.append(k)

        return unique_keywords


if __name__ == "__main__":
    # Test
    from dotenv import load_dotenv
    load_dotenv()

    fetcher = ImageFetcher()

    # Test keyword mapping
    test_keywords = ["federal reserve", "inflation", "nvidia", "oil", "unknown term"]
    for kw in test_keywords:
        mapped = fetcher._map_keyword(kw)
        print(f"{kw} → {mapped}")

    # Test fetch with fallback
    image = fetcher.fetch_with_fallback(["federal reserve", "economy"])
    if image:
        image.save("test_background.png")
        print(f"✅ Saved test background: {image.size}")
