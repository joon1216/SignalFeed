"""
SignalFeed - 글로벌 경제 뉴스 시그널 파이프라인
수집 → 클러스터링 → 생성(Gemini 구조화) → 검증 → 카드 렌더링 → Shorts

지연 로딩(lazy import)을 위해 자동 import 하지 않음.
각 모듈은 필요할 때 명시적으로 import.
"""

__version__ = "2.1.0"
__all__ = [
    "collector",
    "clusterer",
    "content_gen",
    "content_validator",
    "card_renderer",
    "fact_checker",
    "gen_cache",
    "image_fetcher",
    "hook_patterns",
    "shorts_gen",
]
