"""
Tests for backend/modules/content_gen.py
"""

import pytest
import json
import os
import tempfile
from backend.modules.content_gen import ContentGenerator, TemplateFallback


class TestContentGenerator:
    """Test ContentGenerator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = ContentGenerator(api_key=None)  # Use template fallback

        # Sample cluster data
        self.sample_cluster = {
            "cluster_id": 0,
            "cluster_label": "Fed Rate Cut",
            "signal": "bullish",
            "affected_sectors": ["Technology", "Real Estate", "Consumer Discretionary"],
            "articles": [
                {
                    "id": "test-1",
                    "title": "Fed cuts rates",
                    "summary": "Rate cut announced",
                    "signal": "bullish",
                    "confidence": 0.85
                }
            ]
        }

    def test_instagram_script_structure(self):
        """Test Instagram script returns correct structure"""
        script = self.generator.generate_instagram_script(self.sample_cluster)

        # Check top-level keys
        assert "cluster_id" in script
        assert "signal" in script
        assert "slides" in script
        assert "hashtags" in script
        assert "disclaimer" in script

        # Check slides structure
        assert isinstance(script["slides"], list)
        assert len(script["slides"]) == 5

        # Check each slide has required keys
        for slide in script["slides"]:
            assert "slide_num" in slide
            assert "title" in slide
            assert "body" in slide

    def test_instagram_slide_count(self):
        """Test Instagram script has exactly 5 slides"""
        script = self.generator.generate_instagram_script(self.sample_cluster)

        assert len(script["slides"]) == 5

        # Verify slide numbers
        slide_nums = [slide["slide_num"] for slide in script["slides"]]
        assert slide_nums == [1, 2, 3, 4, 5]

    def test_shorts_script_duration(self):
        """Test Shorts script duration is between 50-70 seconds"""
        script = self.generator.generate_shorts_script(self.sample_cluster)

        assert "duration_estimate" in script
        assert 50 <= script["duration_estimate"] <= 70

    def test_disclaimer_present(self):
        """Test disclaimer is present in both Instagram and Shorts output"""
        # Instagram
        instagram = self.generator.generate_instagram_script(self.sample_cluster)
        assert "disclaimer" in instagram
        assert "투자 권유가 아닙니다" in instagram["disclaimer"]

        # Shorts
        shorts = self.generator.generate_shorts_script(self.sample_cluster)
        assert "description" in shorts
        assert "투자 권유가 아닙니다" in shorts["description"]

    def test_no_prediction_words(self):
        """Test banned prediction words are not in output"""
        banned_words = ["예상", "전망", "오를", "떨어질", "추천", "매수", "매도"]

        # Instagram
        instagram = self.generator.generate_instagram_script(self.sample_cluster)
        instagram_text = json.dumps(instagram, ensure_ascii=False)

        for word in banned_words:
            assert word not in instagram_text, f"Banned word '{word}' found in Instagram script"

        # Shorts
        shorts = self.generator.generate_shorts_script(self.sample_cluster)
        shorts_text = json.dumps(shorts, ensure_ascii=False)

        for word in banned_words:
            assert word not in shorts_text, f"Banned word '{word}' found in Shorts script"

    def test_hashtag_count(self):
        """Test Instagram script returns 10 hashtags"""
        script = self.generator.generate_instagram_script(self.sample_cluster)

        assert "hashtags" in script
        assert len(script["hashtags"]) == 10

        # Verify all hashtags start with #
        for hashtag in script["hashtags"]:
            assert hashtag.startswith("#")

    def test_template_fallback(self):
        """Test template fallback works without API key"""
        # Generator without API key
        generator_no_key = ContentGenerator(api_key=None)

        # Should use template fallback
        assert not generator_no_key.use_llm

        # Generate Instagram script
        instagram = generator_no_key.generate_instagram_script(self.sample_cluster)

        # Verify basic structure
        assert "slides" in instagram
        assert len(instagram["slides"]) == 5
        assert "disclaimer" in instagram

        # Generate Shorts script
        shorts = generator_no_key.generate_shorts_script(self.sample_cluster)

        # Verify basic structure
        assert "narration" in shorts
        assert "duration_estimate" in shorts
        assert "title" in shorts

    def test_generate_all(self):
        """Test generate_all processes multiple clusters"""
        clusters = [
            {
                "cluster_id": 0,
                "cluster_label": "Issue 1",
                "signal": "bullish",
                "affected_sectors": ["Tech"],
                "articles": []
            },
            {
                "cluster_id": 1,
                "cluster_label": "Issue 2",
                "signal": "bearish",
                "affected_sectors": ["Finance"],
                "articles": []
            }
        ]

        scripts = self.generator.generate_all(clusters)

        # Verify all clusters processed
        assert len(scripts) == 2

        # Verify each script has instagram and shorts
        for script in scripts:
            assert "instagram" in script
            assert "shorts" in script
            assert "cluster_id" in script

    def test_save_and_load(self):
        """Test save and load roundtrip"""
        scripts = [
            {
                "cluster_id": 0,
                "cluster_label": "Test Issue",
                "signal": "neutral",
                "instagram": {"slides": [], "hashtags": [], "disclaimer": ""},
                "shorts": {"narration": "", "duration_estimate": 60}
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "scripts.json")

            # Save
            self.generator.save(scripts, output_path)

            # Verify file exists
            assert os.path.exists(output_path)

            # Load back
            with open(output_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            # Verify
            assert len(loaded) == 1
            assert loaded[0]["cluster_id"] == 0
            assert loaded[0]["cluster_label"] == "Test Issue"
