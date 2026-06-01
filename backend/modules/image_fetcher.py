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

    # 경제 뉴스 키워드 → Pexels 검색어 매핑 (더 구체적이고 시각적인 키워드)
    KEYWORD_MAPPING = {
        # 금리/연준
        "federal reserve": "federal reserve bank building",
        "interest rate": "federal reserve washington",
        "rate hike": "central bank money policy",
        "FOMC": "federal reserve building exterior",
        "fed": "federal reserve washington",
        "central bank": "federal reserve building",

        # 인플레이션
        "inflation": "dollar bills money close up",
        "CPI": "shopping cart grocery prices",
        "price increase": "supermarket price tag",
        "consumer price": "grocery store shopping",

        # 주식/증시
        "stock market": "stock market trading screen",
        "nasdaq": "stock exchange trading floor",
        "S&P": "wall street bull statue",
        "dow jones": "new york stock exchange nyse",
        "earnings": "financial report business meeting",
        "stock": "stock market digital screen",
        "market": "trading floor wall street",

        # 빅테크
        "nvidia": "computer chip semiconductor close",
        "apple": "apple logo technology",
        "tesla": "electric vehicle charging",
        "microsoft": "technology office modern",
        "google": "technology data center",
        "amazon": "warehouse logistics delivery",
        "meta": "social media smartphone screen",
        "semiconductor": "microchip technology close",
        "chip": "computer chip circuit board",
        "AI": "artificial intelligence technology",

        # 에너지/원자재
        "oil": "oil refinery petroleum industry",
        "energy": "oil pipeline energy infrastructure",
        "gold": "gold bars precious metal",
        "commodity": "raw materials industrial",
        "petroleum": "oil drilling platform",
        "natural gas": "gas pipeline infrastructure",

        # 경제지표
        "GDP": "city skyline economic growth",
        "unemployment": "office workers business district",
        "recession": "empty office business decline",
        "economic growth": "skyscrapers city prosperity",
        "employment": "business district office workers",
        "jobs": "corporate office workplace",

        # 지정학
        "war": "military conflict geopolitics",
        "trade war": "shipping container port cargo",
        "china": "shanghai skyline financial district",
        "europe": "european central bank frankfurt",
        "russia": "moscow city skyscraper",
        "ukraine": "industrial factory production",

        # 한국
        "kospi": "seoul skyline yeouido finance",
        "korea": "seoul city financial district",
        "samsung": "technology electronics innovation",

        # 무역
        "tariff": "cargo port shipping containers",
        "export": "shipping containers international trade",
        "trade": "container ship cargo port",

        # 금융
        "dollar": "us dollar bills currency",
        "treasury": "us treasury building washington",
        "bond": "financial bonds investment",
        "currency": "money exchange foreign currency",

        # 부동산
        "real estate": "modern apartment building",
        "housing": "residential housing development",
        "mortgage": "house keys home loan",

        # 기본
        "default": "financial district skyscraper aerial"
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
        클러스터 데이터에서 Pexels 검색 키워드 추출 (개선된 엔티티 추출)

        Args:
            cluster_data: 클러스터 데이터 (cluster_label, articles)

        Returns:
            검색 키워드 리스트 (우선순위 순, 최대 3개)
        """
        keywords = []
        text_to_analyze = []

        # 1. cluster_label 추가
        cluster_label = cluster_data.get("cluster_label", "")
        if cluster_label and cluster_label != "노이즈":
            text_to_analyze.append(cluster_label.lower())

        # 2. article titles 추가 (첫 3개)
        articles = cluster_data.get("articles", [])
        for article in articles[:3]:
            title = article.get("title", "")
            if title:
                text_to_analyze.append(title.lower())

        # 3. 모든 텍스트에서 매핑된 키워드 추출
        combined_text = " ".join(text_to_analyze)

        # 우선순위 1: KEYWORD_MAPPING에 정확히 있는 키워드
        for key in self.KEYWORD_MAPPING.keys():
            if key in combined_text and key != "default":
                keywords.append(key)
                if len(keywords) >= 3:
                    break

        # 우선순위 2: 부분 매칭 (예: "Federal" → "federal reserve")
        if len(keywords) < 3:
            words = combined_text.split()
            for word in words:
                for key in self.KEYWORD_MAPPING.keys():
                    if word in key or key in word:
                        if key not in keywords and key != "default":
                            keywords.append(key)
                            if len(keywords) >= 3:
                                break
                if len(keywords) >= 3:
                    break

        # 3. Default fallback
        if not keywords:
            keywords.append("default")

        # Deduplicate while preserving order, return max 3
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique_keywords.append(k)
            if len(unique_keywords) >= 3:
                break

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
