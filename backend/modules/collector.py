"""
SignalFeed News Collector
Polygon.io + Finnhub API로 글로벌 경제 뉴스 수집
"""

import os
import time
import uuid
import logging
from typing import List, Dict, Optional
from datetime import datetime
import requests
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsCollector:
    """글로벌 경제 뉴스 수집기 (Polygon.io + Finnhub)"""

    # Source whitelists (strict - macro economic news only)
    POLYGON_WHITELIST = {
        "Reuters",
        "Bloomberg",
        "Financial Times",
        "The Wall Street Journal",
        "CNBC",
        "MarketWatch",
        "Associated Press"
    }

    FINNHUB_WHITELIST = {
        "Reuters",
        "Bloomberg",
        "Financial Times",
        "The Wall Street Journal",
        "CNBC",
        "MarketWatch",
        "Associated Press",
        "AP News"
    }

    # Macro economic keywords for Polygon.io (instead of tickers)
    MACRO_KEYWORDS = [
        "federal reserve", "interest rate", "inflation", "GDP", "employment",
        "S&P 500", "nasdaq", "recession", "economic", "Fed", "FOMC",
        "treasury", "tariff", "trade war", "oil price", "dollar"
    ]

    # Default categories for Finnhub (removed crypto - too specific)
    DEFAULT_CATEGORIES = ["general", "forex", "merger"]

    def __init__(self):
        """Initialize NewsCollector"""
        self.polygon_base_url = "https://api.polygon.io/v2/reference/news"
        self.finnhub_base_url = "https://finnhub.io/api/v1/news"

    def _retry_request(self, func, max_retries=3, initial_delay=1):
        """
        Exponential backoff retry wrapper

        Args:
            func: Function to retry
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds

        Returns:
            Function result or None if all retries fail
        """
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Max retries reached: {e}")
                    return None
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        return None

    def collect_polygon(
        self,
        api_key: str,
        keywords: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Polygon.io에서 매크로 경제 뉴스 수집 (키워드 기반)

        Args:
            api_key: Polygon.io API key
            keywords: 검색 키워드 리스트 (기본값: MACRO_KEYWORDS)
            limit: 최대 기사 수

        Returns:
            List of news articles
        """
        if keywords is None:
            keywords = self.MACRO_KEYWORDS

        all_articles = []
        seen_urls = set()

        # Get yesterday's date for time filtering
        from datetime import datetime, timedelta
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Use general news endpoint (no ticker filter for macro news)
        logger.info(f"Collecting Polygon.io macro economic news (last 24h)...")

        def fetch():
            params = {
                "limit": limit,
                "published_utc.gte": yesterday,
                "apiKey": api_key
            }
            response = requests.get(self.polygon_base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        data = self._retry_request(fetch)

        if data and "results" in data:
            for article in data["results"]:
                # Filter by whitelist
                publisher = article.get("publisher", {}).get("name", "")
                if publisher not in self.POLYGON_WHITELIST:
                    continue

                # Filter by macro keywords in title/description
                title = article.get("title", "").lower()
                description = article.get("description", "").lower()
                text = f"{title} {description}"

                has_keyword = any(keyword.lower() in text for keyword in keywords)
                if not has_keyword:
                    continue

                # Deduplicate by URL
                url = article.get("article_url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Extract fields
                all_articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": url,
                    "published_at": article.get("published_utc", ""),
                    "source": publisher,
                    "tickers": article.get("tickers", []),
                    "raw_source": "polygon"
                })

            logger.info(f"Collected {len(all_articles)} macro articles from Polygon.io")

        logger.info(f"Total Polygon.io articles: {len(all_articles)}")
        return all_articles

    def collect_finnhub(
        self,
        api_key: str,
        categories: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Finnhub에서 뉴스 수집

        Args:
            api_key: Finnhub API key
            categories: 카테고리 리스트 (기본값: DEFAULT_CATEGORIES)
            limit: 카테고리당 최대 기사 수

        Returns:
            List of news articles
        """
        if categories is None:
            categories = self.DEFAULT_CATEGORIES

        all_articles = []

        for category in categories:
            logger.info(f"Collecting Finnhub news for category: {category}...")

            def fetch():
                params = {
                    "category": category,
                    "token": api_key
                }
                response = requests.get(self.finnhub_base_url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()

            data = self._retry_request(fetch)

            if data and isinstance(data, list):
                for article in data[:limit]:
                    # Filter by whitelist
                    source = article.get("source", "")
                    if source not in self.FINNHUB_WHITELIST:
                        continue

                    # Extract fields
                    all_articles.append({
                        "title": article.get("headline", ""),
                        "description": article.get("summary", ""),
                        "url": article.get("url", ""),
                        "published_at": datetime.fromtimestamp(article.get("datetime", 0)).isoformat(),
                        "source": source,
                        "tickers": [],
                        "raw_source": "finnhub"
                    })

                logger.info(f"Collected {len(data[:limit])} articles from Finnhub for {category}")

            # Rate limit: Finnhub free = 60 req/min → no sleep needed

        logger.info(f"Total Finnhub articles: {len(all_articles)}")
        return all_articles

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate title similarity (0-1)

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score (0-1)
        """
        return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()

    def merge_and_deduplicate(
        self,
        polygon_news: List[Dict],
        finnhub_news: List[Dict]
    ) -> List[Dict]:
        """
        두 소스 병합 및 중복 제거

        Args:
            polygon_news: Polygon.io articles
            finnhub_news: Finnhub articles

        Returns:
            Merged and deduplicated articles with unified schema
        """
        all_articles = polygon_news + finnhub_news
        logger.info(f"Total articles before deduplication: {len(all_articles)}")

        # Deduplicate by title similarity (>90%)
        deduplicated = []
        seen_titles = []

        for article in all_articles:
            title = article.get("title", "")
            if not title:
                continue

            # Check similarity with existing titles
            is_duplicate = False
            for seen_title in seen_titles:
                if self._title_similarity(title, seen_title) > 0.9:
                    is_duplicate = True
                    break

            if not is_duplicate:
                # Normalize to unified schema
                normalized = {
                    "id": str(uuid.uuid4()),
                    "title": article.get("title", ""),
                    "summary": article.get("description", ""),
                    "url": article.get("url", ""),
                    "published_at": article.get("published_at", ""),
                    "source": article.get("source", ""),
                    "tickers": article.get("tickers", [])
                }
                deduplicated.append(normalized)
                seen_titles.append(title)

        logger.info(f"Articles after deduplication: {len(deduplicated)}")
        return deduplicated

    def save(self, articles: List[Dict], output_path: str = "data/1_collected/news.jsonl") -> None:
        """
        JSONL 형식으로 저장

        Args:
            articles: List of articles
            output_path: Output file path
        """
        import json
        import os

        # Create directory if not exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save as JSONL (one JSON per line)
        with open(output_path, 'w', encoding='utf-8') as f:
            for article in articles:
                f.write(json.dumps(article, ensure_ascii=False) + '\n')

        logger.info(f"Saved {len(articles)} articles to {output_path}")

    def run(self, polygon_key: str, finnhub_key: str) -> List[Dict]:
        """
        전체 파이프라인 실행: collect → merge → deduplicate → save → return

        Args:
            polygon_key: Polygon.io API key
            finnhub_key: Finnhub API key

        Returns:
            Collected and deduplicated articles
        """
        logger.info("=" * 70)
        logger.info("SignalFeed News Collection Started")
        logger.info("=" * 70)

        # Step 1: Collect from Polygon.io
        polygon_articles = self.collect_polygon(polygon_key)

        # Step 2: Collect from Finnhub
        finnhub_articles = self.collect_finnhub(finnhub_key)

        # Step 3: Merge and deduplicate
        final_articles = self.merge_and_deduplicate(polygon_articles, finnhub_articles)

        # Step 4: Save
        self.save(final_articles)

        logger.info("=" * 70)
        logger.info(f"Collection Complete: {len(final_articles)} articles")
        logger.info("=" * 70)

        return final_articles


if __name__ == "__main__":
    # Test run (requires .env file with API keys)
    from dotenv import load_dotenv
    load_dotenv()

    polygon_key = os.getenv("POLYGON_API_KEY")
    finnhub_key = os.getenv("FINNHUB_API_KEY")

    if not polygon_key or not finnhub_key:
        logger.error("Missing API keys. Please set POLYGON_API_KEY and FINNHUB_API_KEY in .env")
    else:
        collector = NewsCollector()
        articles = collector.run(polygon_key, finnhub_key)
        logger.info(f"Collected {len(articles)} articles")
