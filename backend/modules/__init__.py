"""
IssueFit - 정치 뉴스 이슈 분석 시스템
크롤링 → 클러스터링 → 정치성향 분류 → 다관점 요약

지연 로딩(lazy import)을 위해 자동 import 하지 않음
각 모듈은 필요할 때 명시적으로 import
"""

__version__ = "1.0.0"
__all__ = [
    'crawler',
    'crawler_v3',
    'clawler_ver2',
    'classifier',
    'clusterer',
    'summarizer',
    'db_loader'
]
