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
    # 딥리서치 표3 기반: 이슈의 무드를 시각화하는 구체적 명사/장면 위주
    KEYWORD_MAPPING = {
        # 지정학
        "iran": "diplomacy handshake suit",
        "이란": "diplomacy handshake suit",
        "ceasefire": "bright sunrise city skyline",
        "휴전": "diplomacy handshake global",
        "war": "stormy dark clouds sky",
        "conflict": "stormy dark clouds sky",
        "지정학": "stormy dark clouds city",

        # 유가/에너지
        "oil rise": "oil refinery sunset pump jack",
        "oil fall": "calm ocean aerial clear sky",
        "유가 상승": "oil refinery sunset dark",
        "유가 하락": "calm ocean aerial green",
        "opec": "oil refinery sunset",
        "energy": "oil refinery sunset silhouette",

        # 금리/통화 — 구체적 장소/사물 명사 위주 (추상어는 무관 이미지 매칭됨)
        # 기관명(연준/fed)이 금리 키워드보다 먼저 매칭되도록 순서 유지
        "연준": "federal reserve building washington",
        "fomc": "federal reserve building washington",
        "fed": "federal reserve building washington",
        "rate hike": "skyscraper bank building night city",
        "rate cut": "coins money growth green",
        "금리 인상": "skyscraper bank building night city",
        "금리 인하": "coins money growth green",
        "inflation": "business graph falling red",

        # 환율/무역
        "dollar": "stack coins international container ship",
        "환율": "container ship port daytime",
        "trade": "global trade shipping cargo",
        "tariff": "container ship cargo port",
        "관세": "cargo container ship port",

        # 주식/경제
        "nasdaq": "stock market trading finance blue",
        "market": "stock market trading finance",
        "kospi": "korea stock exchange finance",
        "recession": "business graph falling red dark",

        # AI/반도체
        "ai": "glowing microchip blue server room",
        "semiconductor": "glowing microchip blue neural network",
        "반도체": "microchip technology server room lights",
        "nvidia": "gpu chip technology blue",

        # 중국
        "china": "bustling asian market neon city",
        "중국": "neon city street crowd colorful",

        # 방산
        "defense": "military technology aerospace",
        "방산": "aerospace technology defense",

        # 기본값
        "default": "global economy finance business city",
    }

    # fact_checker 토픽 → 커버 검색어 (Session 45 — 토픽이 키워드의 1순위 소스)
    # 텍스트 부분 문자열 매핑은 섹터/부가 단어('defense' 등)에 오염될 수 있어,
    # 이슈의 매크로 토픽이 감지됐다면 그것을 우선한다.
    TOPIC_KEYWORDS = {
        "유가 상승": "oil refinery sunset pump jack",
        "유가 하락": "calm ocean aerial clear sky",
        "금리 인상": "skyscraper bank building night city",
        "금리 인하": "coins money growth green",
        "달러 강세": "us dollar bills money stack",
        "달러 약세": "currency exchange money global",
        "지정학 리스크": "stormy dark clouds sky",
        "지정학 해소": "bright sunrise city skyline",
        "중국 경기 호조": "shanghai skyline night city",
        "AI 반도체": "glowing microchip blue server room",
    }

    @classmethod
    def keyword_for_topic(cls, topic: Optional[str]) -> Optional[str]:
        """매크로 토픽 → 커버 검색어. 매핑 없는 토픽이면 None"""
        if not topic:
            return None
        return cls.TOPIC_KEYWORDS.get(topic)

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
    # 왜곡/스타일 미스매치 이미지 차단용 태그 블랙리스트 (Session 44)
    # tiny planet 파노라마, 일러스트, 추상 이미지 등이 popular 1위로 선택되던 문제
    BAD_TAGS = (
        "panorama", "panoramic", "360", "fisheye", "fish eye", "planet",
        "sphere", "abstract", "cartoon", "illustration", "drawing", "render",
        "collage", "wallpaper", "map", "flag", "logo", "halloween", "christmas",
    )

    @classmethod
    def score_hit(cls, hit: dict, keyword: str = "") -> float:
        """Pixabay 검색 결과 1건 점수화 — 높을수록 커버 배경으로 적합.

        - 블랙리스트 태그(왜곡 파노라마/일러스트 등) → 건당 -100 (사실상 탈락)
        - 극단적 종횡비(초광각 파노라마 등) → -50
        - 검색어 단어가 태그에 실제로 포함 → 건당 +20 (주제 관련성)
        - 다운로드 수는 약한 가산점 (동률 시 인기순)
        """
        tags = (hit.get("tags") or "").lower()
        score = 0.0
        score -= 100.0 * sum(1 for t in cls.BAD_TAGS if t in tags)
        w, h = hit.get("imageWidth") or 1, hit.get("imageHeight") or 1
        aspect = w / max(h, 1)
        if aspect > 2.2 or aspect < 0.4:
            score -= 50.0
        for word in keyword.lower().split():
            if len(word) >= 4 and word in tags:
                score += 20.0
        score += min((hit.get("downloads") or 0) / 10000.0, 10.0)
        return score

    @classmethod
    def pick_best(cls, hits: list, keyword: str = "") -> Optional[dict]:
        """후보 중 최고 점수 hit. 전부 블랙리스트면 None (fallback 배경 사용)"""
        if not hits:
            return None
        best = max(hits, key=lambda h: cls.score_hit(h, keyword))
        if cls.score_hit(best, keyword) <= -50.0:
            logger.warning("Pixabay 후보 전원 부적합 (왜곡/스타일 미스매치)")
            return None
        return best

    def _query_pixabay(self, keyword: str, with_category: bool = True) -> Optional[str]:
        """Pixabay API 검색 → 스코어링 후 최적 이미지 largeImageURL 반환"""
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
            "per_page": 20,
        }
        if with_category:
            params["category"] = "business"
        try:
            resp = requests.get(self.PIXABAY_API_URL, params=params, timeout=10)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            best = self.pick_best(hits, keyword)
            return best["largeImageURL"] if best else None
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

        for attempt in range(1, 4):
            try:
                img_resp = requests.get(img_url, timeout=15)
                img_resp.raise_for_status()
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(img_resp.content)
                logger.info(f"✅ Pixabay 이미지 저장: {save_path} ('{keyword}')")
                return True
            except Exception as e:
                logger.warning(f"이미지 다운로드 실패 ({attempt}/3) '{keyword}': {e}")
                if attempt < 3:
                    import time
                    time.sleep(5 * attempt)  # 백오프 (429 rate limit 대응)
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
