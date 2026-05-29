"""
Tests for backend/modules/auto_labeler.py
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch
from backend.modules.auto_labeler import AutoLabeler


class TestAutoLabeler:
    """Test AutoLabeler class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.labeler = AutoLabeler()
        self.api_key = "test_api_key"

    def test_label_single_valid_response(self):
        """Test label_single with valid GPT response"""
        # Mock article
        article = {
            "id": "test-1",
            "title": "Apple reports strong earnings",
            "summary": "Apple Inc. beat expectations with Q4 earnings."
        }

        # Mock GPT response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "signal": "bullish",
            "confidence": 0.85,
            "affected_sectors": ["Technology", "Consumer Electronics"],
            "reason": "Strong earnings beat expectations"
        })

        with patch('backend.modules.auto_labeler.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Label
            result = self.labeler.label_single(article, self.api_key)

            # Verify fields added
            assert result["signal"] == "bullish"
            assert result["confidence"] == 0.85
            assert result["affected_sectors"] == ["Technology", "Consumer Electronics"]
            assert result["label_reason"] == "Strong earnings beat expectations"

    def test_label_single_invalid_json(self):
        """Test label_single with invalid GPT response (garbage)"""
        article = {
            "id": "test-2",
            "title": "Test article",
            "summary": "Test summary"
        }

        # Mock GPT returning garbage
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is not valid JSON {invalid}"

        with patch('backend.modules.auto_labeler.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Label
            result = self.labeler.label_single(article, self.api_key)

            # Verify fallback to neutral
            assert result["signal"] == "neutral"
            assert result["confidence"] == 0.0
            assert result["affected_sectors"] == []
            assert "Failed to parse" in result["label_reason"]

    def test_label_batch_size(self):
        """Test label_batch processes correct number of articles"""
        articles = [
            {"id": f"test-{i}", "title": f"Article {i}", "summary": f"Summary {i}"}
            for i in range(5)
        ]

        # Mock label_single to return article with signal
        def mock_label_single(article, api_key):
            article["signal"] = "neutral"
            article["confidence"] = 0.5
            article["affected_sectors"] = []
            article["label_reason"] = "Test"
            return article

        with patch.object(self.labeler, 'label_single', side_effect=mock_label_single):
            result = self.labeler.label_batch(articles, self.api_key, batch_size=2)

            # Verify all articles processed
            assert len(result) == 5
            assert all("signal" in a for a in result)

    def test_validate_labels_distribution(self):
        """Test validate_labels calculates distribution correctly"""
        articles = [
            {"id": "1", "signal": "bullish", "confidence": 0.8},
            {"id": "2", "signal": "bullish", "confidence": 0.9},
            {"id": "3", "signal": "bearish", "confidence": 0.7},
            {"id": "4", "signal": "neutral", "confidence": 0.6},
            {"id": "5", "signal": "neutral", "confidence": 0.5}
        ]

        stats = self.labeler.validate_labels(articles)

        # Check distribution
        assert stats["total"] == 5
        assert stats["distribution"]["bullish"] == 2
        assert stats["distribution"]["bearish"] == 1
        assert stats["distribution"]["neutral"] == 2

        # Check average confidence
        assert stats["avg_confidence"]["bullish"] == pytest.approx(0.85, 0.01)
        assert stats["avg_confidence"]["bearish"] == pytest.approx(0.7, 0.01)
        assert stats["avg_confidence"]["neutral"] == pytest.approx(0.55, 0.01)

    def test_validate_labels_low_confidence(self):
        """Test validate_labels flags low confidence articles"""
        articles = [
            {"id": "1", "signal": "bullish", "confidence": 0.8},  # Good
            {"id": "2", "signal": "bearish", "confidence": 0.5},  # Low
            {"id": "3", "signal": "neutral", "confidence": 0.3},  # Low
            {"id": "4", "signal": "bullish", "confidence": 0.9},  # Good
        ]

        stats = self.labeler.validate_labels(articles)

        # Check low confidence count
        assert stats["low_confidence_count"] == 2

        # Check needs_review flag
        assert articles[0]["needs_review"] is False
        assert articles[1]["needs_review"] is True
        assert articles[2]["needs_review"] is True
        assert articles[3]["needs_review"] is False

    def test_save_and_load(self):
        """Test JSONL save and load roundtrip with labeled data"""
        articles = [
            {
                "id": "test-1",
                "title": "Article 1",
                "summary": "Summary 1",
                "signal": "bullish",
                "confidence": 0.85,
                "affected_sectors": ["Tech"],
                "label_reason": "Strong performance",
                "needs_review": False
            },
            {
                "id": "test-2",
                "title": "Article 2",
                "summary": "Summary 2",
                "signal": "bearish",
                "confidence": 0.7,
                "affected_sectors": ["Finance"],
                "label_reason": "Declining metrics",
                "needs_review": False
            }
        ]

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            temp_path = f.name

        try:
            # Save
            self.labeler.save(articles, temp_path)

            # Load back
            loaded = []
            with open(temp_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        loaded.append(json.loads(line))

            # Verify
            assert len(loaded) == 2
            assert loaded[0]["signal"] == "bullish"
            assert loaded[0]["confidence"] == 0.85
            assert loaded[1]["signal"] == "bearish"
            assert loaded[1]["affected_sectors"] == ["Finance"]

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
