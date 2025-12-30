"""
IssueFit - 정치 뉴스 이슈 분석 시스템
크롤링 → 클러스터링 → 정치성향 분류 → 다관점 요약
"""

from .crawler import NaverNewsCrawler, crawl_political_news
from .classifier import PoliticalClassifier
from .summarizer import PoliticalNewsSummarizer
from .db_loader import load_to_database

__version__ = "1.0.0"
__all__ = [
    'NaverNewsCrawler',
    'crawl_political_news',
    'PoliticalClassifier', 
    'PoliticalNewsSummarizer', 
    'load_to_database'
]
