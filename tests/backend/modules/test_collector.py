"""
Tests for backend/modules/collector.py
"""

import pytest
import json
import os
import tempfile
from backend.modules.collector import NewsCollector


class TestNewsCollector:
    """Test NewsCollector class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.collector = NewsCollector()

    def test_merge_and_deduplicate(self):
        """Test merge_and_deduplicate deduplication logic"""
        # Polygon articles
        polygon_news = [
            {
                "title": "Apple stock rises 2% on earnings",
                "description": "Apple reported strong Q4 earnings",
                "url": "https://polygon.io/apple-1",
                "published_at": "2024-01-01T10:00:00Z",
                "source": "Reuters",
                "tickers": ["AAPL"]
            },
            {
                "title": "Tesla unveils new Model Y",
                "description": "Tesla launches updated Model Y",
                "url": "https://polygon.io/tesla-1",
                "published_at": "2024-01-01T11:00:00Z",
                "source": "Bloomberg",
                "tickers": ["TSLA"]
            }
        ]

        # Finnhub articles (one duplicate, one unique)
        finnhub_news = [
            {
                "title": "Apple stock rises 2.5% on earnings",  # Similar to polygon article
                "description": "Apple beats Q4 expectations",
                "url": "https://finnhub.io/apple-1",
                "published_at": "2024-01-01T10:05:00Z",
                "source": "CNBC",
                "tickers": []
            },
            {
                "title": "NVIDIA announces new AI chip",
                "description": "NVIDIA launches next-gen GPU",
                "url": "https://finnhub.io/nvidia-1",
                "published_at": "2024-01-01T12:00:00Z",
                "source": "MarketWatch",
                "tickers": []
            }
        ]

        # Merge and deduplicate
        result = self.collector.merge_and_deduplicate(polygon_news, finnhub_news)

        # Should have 3 unique articles (Apple duplicate removed)
        assert len(result) == 3

        # Check unified schema
        for article in result:
            assert "id" in article
            assert "title" in article
            assert "summary" in article
            assert "url" in article
            assert "published_at" in article
            assert "source" in article
            assert "tickers" in article

    def test_save_and_load(self):
        """Test JSONL save and load roundtrip"""
        # Create test articles
        test_articles = [
            {
                "id": "test-1",
                "title": "Test Article 1",
                "summary": "Summary 1",
                "url": "https://example.com/1",
                "published_at": "2024-01-01T10:00:00Z",
                "source": "Reuters",
                "tickers": ["AAPL"]
            },
            {
                "id": "test-2",
                "title": "Test Article 2",
                "summary": "Summary 2",
                "url": "https://example.com/2",
                "published_at": "2024-01-01T11:00:00Z",
                "source": "Bloomberg",
                "tickers": ["TSLA"]
            }
        ]

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            temp_path = f.name

        try:
            # Save
            self.collector.save(test_articles, temp_path)

            # Load back
            loaded_articles = []
            with open(temp_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        loaded_articles.append(json.loads(line))

            # Verify
            assert len(loaded_articles) == len(test_articles)
            assert loaded_articles[0]["id"] == "test-1"
            assert loaded_articles[1]["title"] == "Test Article 2"

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_whitelist_filter(self):
        """Test that merge preserves distinct articles (tests unified schema)"""
        # Mock Polygon articles with very different titles
        polygon_news = [
            {
                "title": "Apple quarterly earnings exceed expectations significantly",
                "description": "From Reuters",
                "url": "https://example.com/1",
                "published_at": "2024-01-01T10:00:00Z",
                "source": "Reuters",
                "tickers": ["AAPL"]
            },
            {
                "title": "Tesla unveils groundbreaking Model Y design",
                "description": "From Bloomberg",
                "url": "https://example.com/2",
                "published_at": "2024-01-01T11:00:00Z",
                "source": "Bloomberg",
                "tickers": ["TSLA"]
            }
        ]

        finnhub_news = []

        # Merge and deduplicate
        result = self.collector.merge_and_deduplicate(polygon_news, finnhub_news)

        # Both distinct articles should be preserved
        assert len(result) == 2
        assert all("id" in a for a in result)  # Unified schema
        assert all("title" in a and "summary" in a for a in result)

    def test_title_similarity(self):
        """Test title similarity calculation"""
        # Exact match
        assert self.collector._title_similarity("Apple stock rises", "Apple stock rises") == 1.0

        # Very similar
        similarity = self.collector._title_similarity(
            "Apple stock rises 2%",
            "Apple stock rises 2.5%"
        )
        assert similarity > 0.9

        # Different
        similarity = self.collector._title_similarity(
            "Apple stock rises",
            "Tesla unveils new car"
        )
        assert similarity < 0.5
