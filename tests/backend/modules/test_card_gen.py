"""
Tests for backend/modules/card_gen.py
"""

import pytest
import os
import tempfile
from PIL import Image
from backend.modules.card_gen import CardGenerator


class TestCardGenerator:
    """Test CardGenerator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = CardGenerator()

        # Sample Instagram script
        self.sample_script = {
            "cluster_id": "0",
            "signal": "bullish",
            "slides": [
                {
                    "slide_num": 1,
                    "title": "Fed Rate Cut",
                    "body": "BULLISH 시그널 발생",
                    "signal_emoji": "🟢"
                },
                {
                    "slide_num": 2,
                    "title": "호재 요인",
                    "body": "• 경제 성장 지표 개선\n• 기업 실적 증가\n• 정책 지원 확대",
                    "sectors": ["Technology", "Real Estate"]
                },
                {
                    "slide_num": 3,
                    "title": "악재 요인",
                    "body": "• 인플레이션 우려\n• 금리 인상 압력\n• 글로벌 불확실성",
                    "sectors": []
                },
                {
                    "slide_num": 4,
                    "title": "중립 요인",
                    "body": "• 시장 관망세 지속\n• 혼조세 나타남\n• 변동성 확대 가능",
                    "caution": "AI 분석 결과이며, 실제 시장 상황과 다를 수 있습니다."
                },
                {
                    "slide_num": 5,
                    "title": "요약",
                    "body": "Fed Rate Cut\n\nBULLISH 시그널\n\n모든 투자 판단은 본인 책임입니다.",
                    "cta": "자세한 분석 → 프로필 링크"
                }
            ],
            "disclaimer": "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
        }

    def test_slide_dimensions(self):
        """Test each slide is 1080x1920px"""
        slides = self.generator.generate_all_slides(self.sample_script)

        for slide in slides:
            assert slide.size == (1080, 1920), f"Expected (1080, 1920), got {slide.size}"

    def test_slide_count(self):
        """Test generate_all_slides returns exactly 5 slides"""
        slides = self.generator.generate_all_slides(self.sample_script)

        assert len(slides) == 5

    def test_slide_is_image(self):
        """Test output is PIL Image"""
        slide = self.generator.generate_slide1_cover(self.sample_script)

        assert isinstance(slide, Image.Image)

    def test_save_creates_files(self):
        """Test PNG files are created in correct path"""
        slides = self.generator.generate_all_slides(self.sample_script)

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self.generator.save_slides(slides, "test_cluster", output_dir=tmpdir)

            # Verify 5 files created
            assert len(paths) == 5

            # Verify files exist
            for path in paths:
                assert os.path.exists(path)
                assert path.endswith(".png")

            # Verify directory structure
            cluster_dir = os.path.join(tmpdir, "cluster_test_cluster")
            assert os.path.isdir(cluster_dir)

    def test_hex_to_rgb(self):
        """Test hex to RGB conversion is correct"""
        # Test white
        assert self.generator._hex_to_rgb("#FFFFFF") == (255, 255, 255)

        # Test black
        assert self.generator._hex_to_rgb("#000000") == (0, 0, 0)

        # Test brand green
        assert self.generator._hex_to_rgb("#00C853") == (0, 200, 83)

        # Test with leading #
        assert self.generator._hex_to_rgb("#FF3D3D") == (255, 61, 61)

    def test_all_slides_dark_bg(self):
        """Test all slides have dark background (#121212 ± 10)"""
        slides = self.generator.generate_all_slides(self.sample_script)

        # Expected background color
        expected_bg = self.generator._hex_to_rgb("#121212")

        for i, slide in enumerate(slides, start=1):
            # Check top-left pixel
            pixel = slide.getpixel((0, 0))

            # Allow ±10 tolerance for each channel
            for j in range(3):
                assert abs(pixel[j] - expected_bg[j]) <= 10, \
                    f"Slide {i} background pixel {pixel} not close to {expected_bg}"
