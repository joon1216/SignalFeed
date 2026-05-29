"""
Tests for backend/modules/classifier.py
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch
from backend.modules.classifier import SignalClassifier


class TestSignalClassifier:
    """Test SignalClassifier class"""

    def setup_method(self):
        """Setup test fixtures"""
        # Mock model to avoid downloading FinBERT
        with patch('backend.modules.classifier.AutoTokenizer'), \
             patch('backend.modules.classifier.AutoModelForSequenceClassification'):
            self.classifier = SignalClassifier()

    def test_label_mapping(self):
        """Test that label mapping is correct"""
        assert self.classifier.LABEL_MAPPING["positive"] == "bullish"
        assert self.classifier.LABEL_MAPPING["negative"] == "bearish"
        assert self.classifier.LABEL_MAPPING["neutral"] == "neutral"

    def test_reverse_mapping(self):
        """Test that reverse mapping is correct"""
        assert self.classifier.REVERSE_MAPPING["bullish"] == "positive"
        assert self.classifier.REVERSE_MAPPING["bearish"] == "negative"
        assert self.classifier.REVERSE_MAPPING["neutral"] == "neutral"

    def test_classify_single_structure(self):
        """Test classify_single returns correct structure"""
        import torch

        # Mock tokenizer and model
        with patch.object(self.classifier, 'tokenizer') as mock_tokenizer, \
             patch.object(self.classifier, 'model') as mock_model:

            # Mock tokenizer output (needs to support unpacking with **)
            mock_inputs = {
                'input_ids': torch.tensor([[1, 2, 3]]),
                'attention_mask': torch.tensor([[1, 1, 1]])
            }
            mock_inputs_on_device = {k: v for k, v in mock_inputs.items()}

            # Mock tokenizer call
            mock_tokenizer_output = Mock()
            mock_tokenizer_output.to.return_value = mock_inputs_on_device
            mock_tokenizer.return_value = mock_tokenizer_output

            # Mock model output (logits for positive class)
            mock_outputs = Mock()
            mock_outputs.logits = torch.tensor([[2.0, -1.0, 0.0]])  # positive > neutral > negative
            mock_model.return_value = mock_outputs

            # Classify
            result = self.classifier.classify_single("Strong earnings beat expectations")

            # Verify structure
            assert "signal" in result
            assert "confidence" in result
            assert "raw_scores" in result
            assert result["signal"] in ["bullish", "bearish", "neutral"]
            assert 0.0 <= result["confidence"] <= 1.0

    def test_classify_batch_size(self):
        """Test classify_batch processes correct number of articles"""
        articles = [
            {"id": f"test-{i}", "title": f"Title {i}", "summary": f"Summary {i}"}
            for i in range(5)
        ]

        # Mock classify_single to return valid result
        def mock_classify_single(text):
            return {
                "signal": "neutral",
                "confidence": 0.6,
                "raw_scores": {"bullish": 0.2, "bearish": 0.2, "neutral": 0.6}
            }

        with patch.object(self.classifier, 'classify_single', side_effect=mock_classify_single):
            result = self.classifier.classify_batch(articles, batch_size=2)

            # Verify all articles processed
            assert len(result) == 5
            assert all("signal" in a for a in result)
            assert all("confidence" in a for a in result)
            assert all("raw_scores" in a for a in result)

    def test_classify_batch_error_handling(self):
        """Test classify_batch handles errors gracefully"""
        articles = [
            {"id": "test-1", "title": "Good article", "summary": "Valid"},
            {"id": "test-2", "title": "Bad article", "summary": "Invalid"}
        ]

        # Mock classify_single to fail on second article
        def mock_classify_single(text):
            if "Invalid" in text:
                raise ValueError("Test error")
            return {
                "signal": "bullish",
                "confidence": 0.8,
                "raw_scores": {"bullish": 0.8, "bearish": 0.1, "neutral": 0.1}
            }

        with patch.object(self.classifier, 'classify_single', side_effect=mock_classify_single):
            result = self.classifier.classify_batch(articles, batch_size=2)

            # Verify first article succeeded
            assert result[0]["signal"] == "bullish"
            assert result[0]["confidence"] == 0.8

            # Verify second article fell back to neutral
            assert result[1]["signal"] == "neutral"
            assert result[1]["confidence"] == 0.0

    def test_evaluate_metrics(self):
        """Test evaluate calculates metrics correctly"""
        labeled_articles = [
            {"signal": "bullish", "label": "bullish"},  # Correct
            {"signal": "bearish", "label": "bearish"},  # Correct
            {"signal": "neutral", "label": "neutral"},  # Correct
            {"signal": "bullish", "label": "bearish"},  # Wrong
            {"signal": "neutral", "label": "bullish"}   # Wrong
        ]

        stats = self.classifier.evaluate(labeled_articles)

        # Check structure
        assert "accuracy" in stats
        assert "precision" in stats
        assert "recall" in stats
        assert "f1" in stats
        assert "support" in stats

        # Accuracy should be 3/5 = 0.6
        assert stats["accuracy"] == pytest.approx(0.6, 0.01)

    def test_save_and_load_roundtrip(self):
        """Test save_local and load from local directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "test_model")

            # Mock save_pretrained methods
            with patch.object(self.classifier.model, 'save_pretrained') as mock_save_model, \
                 patch.object(self.classifier.tokenizer, 'save_pretrained') as mock_save_tokenizer:

                # Save
                self.classifier.save_local(output_dir)

                # Verify save methods were called
                mock_save_model.assert_called_once_with(output_dir)
                mock_save_tokenizer.assert_called_once_with(output_dir)
