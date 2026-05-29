"""
Tests for backend/modules/fake_filter.py
"""

import pytest
from backend.modules.fake_filter import FakeNewsFilter


class TestFakeNewsFilter:
    """Test FakeNewsFilter class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.filter = FakeNewsFilter()

    def test_layer1_whitelist(self):
        """Test Layer 1: Source whitelist filtering"""
        test_articles = [
            {
                "id": "1",
                "title": "Test Article 1",
                "source": "Reuters"
            },
            {
                "id": "2",
                "title": "Test Article 2",
                "source": "Bloomberg"
            },
            {
                "id": "3",
                "title": "Test Article 3",
                "source": "Unknown Blog"
            },
            {
                "id": "4",
                "title": "Test Article 4",
                "source": "Random Website"
            }
        ]

        # Apply Layer 1
        filtered = self.filter.layer1_whitelist(test_articles)

        # Should keep only whitelisted sources (Reuters, Bloomberg)
        assert len(filtered) == 2
        assert all(a["source"] in self.filter.SOURCE_WHITELIST for a in filtered)

    def test_layer2_cross_validate(self):
        """Test Layer 2: Cross-validation (minimum 3 sources)"""
        test_articles = [
            # Group 1: 3 similar articles from different sources (should be confirmed)
            {
                "id": "1",
                "title": "Apple stock rises 2% on earnings",
                "source": "Reuters"
            },
            {
                "id": "2",
                "title": "Apple stock rises 2.5% after earnings",
                "source": "Bloomberg"
            },
            {
                "id": "3",
                "title": "Apple shares up 2% on strong earnings",
                "source": "CNBC"
            },
            # Group 2: Single article (should be unconfirmed)
            {
                "id": "4",
                "title": "Tesla unveils new Model Y",
                "source": "MarketWatch"
            },
            # Group 3: 2 similar articles (should be unconfirmed, <3 sources)
            {
                "id": "5",
                "title": "NVIDIA launches new AI chip",
                "source": "Reuters"
            },
            {
                "id": "6",
                "title": "NVIDIA announces new AI chip",
                "source": "Bloomberg"
            }
        ]

        # Apply Layer 2
        result = self.filter.layer2_cross_validate(test_articles, min_sources=3)

        # Check Group 1 (Apple) - should be confirmed (3 unique sources)
        apple_articles = [a for a in result if "Apple" in a["title"]]
        assert len(apple_articles) == 3
        assert all(a["confirmed"] for a in apple_articles)

        # Check Group 2 (Tesla) - should be unconfirmed (1 source)
        tesla_articles = [a for a in result if "Tesla" in a["title"]]
        assert len(tesla_articles) == 1
        assert not tesla_articles[0]["confirmed"]

        # Check Group 3 (NVIDIA) - should be unconfirmed (2 sources < 3)
        nvidia_articles = [a for a in result if "NVIDIA" in a["title"]]
        assert len(nvidia_articles) == 2
        assert all(not a["confirmed"] for a in nvidia_articles)

    def test_layer4_anomaly_detect(self):
        """Test Layer 4: Anomaly detection for extreme values"""
        test_articles = [
            # Normal article (no anomaly)
            {
                "id": "1",
                "title": "Apple stock rises 2% on earnings",
                "summary": "Apple reported Q4 earnings beat, stock up 2.3%",
                "source": "Reuters"
            },
            # Anomaly: extreme percentage
            {
                "id": "2",
                "title": "Tesla stock jumps 500% in one day",
                "summary": "Tesla shares skyrocket 500% amid speculation",
                "source": "Unknown Blog"
            },
            # Anomaly: very large number
            {
                "id": "3",
                "title": "Company valued at 50000 billion dollars",
                "summary": "New tech startup valued at 50000 billion",
                "source": "Reuters"
            },
            # Normal article (moderate change)
            {
                "id": "4",
                "title": "Fed raises rates by 0.25%",
                "summary": "Federal Reserve announces 0.25% rate hike",
                "source": "Bloomberg"
            }
        ]

        # Apply Layer 4
        result = self.filter.layer4_anomaly_detect(test_articles)

        # Check flagging
        assert not result[0]["anomaly_flagged"]  # Normal (2%)
        assert result[1]["anomaly_flagged"]      # Anomaly (500%)
        assert result[2]["anomaly_flagged"]      # Anomaly (50000)
        assert not result[3]["anomaly_flagged"]  # Normal (0.25%)

    def test_layer5_disclaimer(self):
        """Test Layer 5: Disclaimer addition"""
        test_articles = [
            {
                "id": "1",
                "title": "Test Article 1",
                "source": "Reuters"
            },
            {
                "id": "2",
                "title": "Test Article 2",
                "source": "Bloomberg"
            }
        ]

        # Apply Layer 5
        result = self.filter.layer5_disclaimer(test_articles)

        # All articles should have disclaimer
        assert len(result) == 2
        assert all("disclaimer" in a for a in result)
        assert all(a["disclaimer"] == "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다" for a in result)

    def test_run_all_layers(self):
        """Test full pipeline (all 5 layers)"""
        test_articles = [
            {
                "id": "1",
                "title": "Apple stock rises 2% on earnings beat",
                "summary": "Apple Q4 results beat expectations",
                "source": "Reuters"
            },
            {
                "id": "2",
                "title": "Apple stock rises 2.1% on earnings beat",
                "summary": "Apple reports strong quarter",
                "source": "Bloomberg"
            },
            {
                "id": "3",
                "title": "Apple stock rises 2.2% on earnings beat",
                "summary": "Apple exceeds Q4 forecasts",
                "source": "CNBC"
            },
            {
                "id": "4",
                "title": "Unknown stock jumps 1000%",
                "summary": "Random stock soars 1000%",
                "source": "Unknown Blog"  # Will be filtered in Layer 1
            }
        ]

        # Run all layers
        result = self.filter.run(test_articles, openai_key=None)

        # Layer 1 should filter Unknown Blog → 3 articles remain
        assert len(result) == 3

        # All remaining articles should have:
        # - confirmed=True (3 unique sources for similar Apple articles, >70% similarity)
        # - anomaly_flagged=False (no extreme values, 2% is normal)
        # - disclaimer
        for article in result:
            assert article.get("confirmed") is True  # 3 similar titles from different sources
            assert article.get("anomaly_flagged") is False  # 2% is not anomaly
            assert "disclaimer" in article

    def test_extract_numbers(self):
        """Test number extraction from text"""
        text = "Stock rises 2.5% to $150, up +10% from last week"
        numbers = self.filter._extract_numbers(text)

        # Should extract: 2.5, 150, 10
        assert 2.5 in numbers
        assert 150.0 in numbers
        assert 10.0 in numbers
