"""
Pixabay API 이미지 검색 및 다운로드
Instagram 카드 배경 이미지 자동 수집 (이슈 유형별 키워드 매핑)
"""

import os
import requests
from PIL import Image
from io import BytesIO
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ImageFetcher:
    """Pixabay API로 키워드 기반 이미지 검색 및 다운로드"""

    PIXABAY_API_URL = "https://pixabay.com/api/"

    # 이슈 유형별 키워드 매핑 (한국어 + 영어 키 → Pixabay 검색어)
    # 주의: Pixabay business 카테고리는 추상어("diplomacy", "geopolitics")에
    # 약하므로 구체적이고 사진성이 강한 명사 위주로 매핑한다.
    KEYWORD_MAPPING = {
        # 지정학/전쟁/분쟁 → 중동 스카이라인/에너지 (군사 사진은 business 카테고리에 빈약)
        "iran": "dubai skyline city",
        "israel": "dubai skyline city",
        "중동": "dubai skyline city",
        "war": "oil refinery industry",
        "conflict": "oil refinery industry",
        "military": "oil refinery industry",
        "지정학": "global economy finance business",
        "전쟁": "oil refinery industry",

        # 금리/통화정책
        "fed": "federal reserve central bank",
        "federal reserve": "federal reserve central bank",
        "fomc": "federal reserve central bank",
        "rate": "federal reserve central bank",
        "금리": "federal reserve central bank",
        "inflation": "economy inflation prices",
        "인플레이션": "economy inflation prices",
        "고물가": "economy inflation prices",

        # 유가/에너지
        "oil": "oil refinery industry",
        "유가": "oil refinery industry",
        "opec": "oil refinery industry",
        "energy": "oil refinery industry",
        "에너지": "oil refinery industry",

        # 무역/관세
        "tariff": "cargo ship port trade",
        "trade": "cargo ship port trade",
        "관세": "cargo ship port trade",
        "수출": "cargo ship port trade",
        "무역": "cargo ship port trade",

        # 주식/금융시장
        "nasdaq": "stock market trading",
        "kospi": "stock market trading",
        "코스피": "stock market trading",
        "market": "stock market trading",
        "증시": "stock market trading",
        "주식": "stock market trading",

        # AI/반도체
        "ai": "artificial intelligence technology",
        "semiconductor": "semiconductor chip technology",
        "반도체": "semiconductor chip technology",
        "chip": "semiconductor chip technology",
        "ipo": "stock market trading",

        # 중국/이머징
        "china": "china economy business",
        "중국": "china economy business",
        "emerging": "global economy finance business",

        # 기본값
        "default": "global economy finance business",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ImageFetcher

        Args:
            api_key: Pixabay API key (defaults to PIXABAY_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("PIXABAY_API_KEY")
        if not self.api_key:
            logger.warning("PIXABAY_API_KEY not found, will use fallback backgrounds")

    # ──────────────────────────────────────────────────────────────
    # 키워드 매핑
    # ──────────────────────────────────────────────────────────────
    def get_keyword(self, issue_text: str) -> str:
        """이슈 텍스트(hook_title + macro_issue 등)에서 Pixabay 검색어 선택"""
        issue_lower = issue_text.lower()
        for key, keyword in self.KEYWORD_MAPPING.items():
            if key == "default":
                continue
            if key in issue_lower:
                logger.info(f"키워드 매핑: '{key}' → '{keyword}'")
                return keyword
        return self.KEYWORD_MAPPING["default"]

    # 하위 호환: 기존 코드가 _map_keyword를 사용할 수 있음
    def _map_keyword(self, keyword: str) -> str:
        return self.get_keyword(keyword)

    # ──────────────────────────────────────────────────────────────
    # 다운로드
    # ──────────────────────────────────────────────────────────────
    def _query_pixabay(self, keyword: str, with_category: bool = True) -> Optional[str]:
        """Pixabay API 검색 → 첫 이미지 largeImageURL 반환"""
        if not self.api_key:
            return None
        params = {
            "key": self.api_key,
            "q": keyword,
            "image_type": "photo",
            "orientation": "vertical",
            "min_width": 1080,
            "safesearch": "true",
            "order": "popular",
            "per_page": 10,
        }
        if with_category:
            params["category"] = "business"
        try:
            resp = requests.get(self.PIXABAY_API_URL, params=params, timeout=10)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            if hits:
                return hits[0]["largeImageURL"]
            return None
        except Exception as e:
            logger.error(f"Pixabay 검색 실패 '{keyword}': {e}")
            return None

    def fetch(self, keyword: str, save_path: str) -> bool:
        """
        Pixabay 이미지 검색 후 save_path에 저장

        Args:
            keyword: 검색 키워드
            save_path: 저장 경로

        Returns:
            성공 여부 (bool)
        """
        if not self.api_key:
            logger.warning("No Pixabay API key")
            return False

        # 1차: category=business / 2차: category 없이 재시도
        img_url = self._query_pixabay(keyword, with_category=True)
        if not img_url:
            img_url = self._query_pixabay(keyword, with_category=False)
        if not img_url:
            logger.warning(f"No photos found for keyword: {keyword}")
            return False

        try:
            img_resp = requests.get(img_url, timeout=15)
            img_resp.raise_for_status()
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(img_resp.content)
            logger.info(f"✅ Pixabay 이미지 저장: {save_path} ('{keyword}')")
            return True
        except Exception as e:
            logger.error(f"이미지 다운로드 실패 '{keyword}': {e}")
            return False

    def fetch_image(self, keyword: str) -> Optional[Image.Image]:
        """Pixabay 이미지를 PIL Image로 반환 (in-memory 사용처용)"""
        img_url = self._query_pixabay(keyword, with_category=True)
        if not img_url:
            img_url = self._query_pixabay(keyword, with_category=False)
        if not img_url:
            return None
        try:
            img_resp = requests.get(img_url, timeout=15)
            img_resp.raise_for_status()
            return Image.open(BytesIO(img_resp.content)).convert("RGB")
        except Exception as e:
            logger.error(f"이미지 로드 실패 '{keyword}': {e}")
            return None

    def fetch_with_fallback(self, keywords: List[str]) -> Image.Image:
        """
        여러 키워드 시도 후 fallback 배경 반환 (하위 호환)

        Args:
            keywords: 검색 키워드 리스트 (우선순위 순)

        Returns:
            PIL Image object, 모두 실패 시 단색 dark bg
        """
        for keyword in keywords:
            mapped = self.get_keyword(keyword)
            image = self.fetch_image(mapped)
            if image:
                return image
        logger.warning("All keywords failed, using fallback background")
        return self._create_fallback_background()

    def save_fallback(self, save_path: str) -> None:
        """단색 dark bg를 save_path에 저장"""
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        self._create_fallback_background().save(save_path, quality=90)

    def _create_fallback_background(self) -> Image.Image:
        """Fallback 배경 이미지 (단색 dark bg, 1080x1350px)"""
        return Image.new("RGB", (1080, 1350), "#1A1A1A")

    def extract_keywords_from_cluster(self, cluster_data: dict) -> List[str]:
        """
        클러스터 데이터에서 검색 키워드 추출 (하위 호환)

        Returns:
            검색 키워드 리스트 (우선순위 순, 최대 3개)
        """
        text_parts = []
        cluster_label = cluster_data.get("cluster_label", "")
        if cluster_label and cluster_label != "노이즈":
            text_parts.append(cluster_label)
        for article in cluster_data.get("articles", [])[:3]:
            title = article.get("title", "")
            if title:
                text_parts.append(title)

        combined = " ".join(text_parts)
        keyword = self.get_keyword(combined)
        return [keyword]


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    fetcher = ImageFetcher()

    # 키워드 매핑 테스트
    tests = ["중동 불안 고조", "Fed 금리 인상", "유가 급등", "AI 반도체 광풍", "unknown term"]
    for t in tests:
        print(f"{t} → {fetcher.get_keyword(t)}")

    # 다운로드 테스트
    ok = fetcher.fetch(fetcher.get_keyword("중동 지정학"), "test_background.jpg")
    print(f"fetch success: {ok}")
