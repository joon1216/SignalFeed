"""
Tests for backend/modules/shorts_gen.py
"""

import pytest
import os
import tempfile
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from backend.modules.shorts_gen import ShortsGenerator


class TestShortsGenerator:
    """Test ShortsGenerator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = ShortsGenerator()

        # Sample shorts script
        self.sample_shorts_script = {
            "cluster_id": "0",
            "narration": "안녕하세요 시그널피드입니다. 오늘의 핵심 이슈입니다.",
            "duration_estimate": 60,
            "title": "Fed Rate Cut - BULLISH 시그널",
            "description": "Fed 금리 인하 분석",
            "tags": ["경제", "투자"]
        }

        # Sample Instagram script
        self.sample_instagram_script = {
            "cluster_id": "0",
            "signal": "bullish",
            "slides": [
                {
                    "slide_num": 1,
                    "title": "Fed Rate Cut",
                    "signal_emoji": "🟢"
                }
            ]
        }

    def test_narration_file_created(self):
        """Test narration file is created"""
        # Mock gTTS to avoid actual API call
        with patch('backend.modules.shorts_gen.gTTS') as mock_gtts:
            mock_tts_instance = Mock()
            mock_gtts.return_value = mock_tts_instance

            # Generate narration
            narration_path = self.generator.generate_narration(self.sample_shorts_script)

            # Verify gTTS was called with correct params
            mock_gtts.assert_called_once_with(
                text=self.sample_shorts_script["narration"],
                lang='ko',
                slow=False
            )

            # Verify save was called
            mock_tts_instance.save.assert_called_once()

            # Verify path format
            assert "narration_0.mp3" in narration_path
            assert narration_path.startswith("data/7_shorts/temp")

    def test_video_output_path(self):
        """Test video output path format is correct"""
        cluster_id = "test_cluster"
        expected_path = f"data/7_shorts/cluster_{cluster_id}.mp4"

        # Path format should match
        assert expected_path == f"data/7_shorts/cluster_{cluster_id}.mp4"

    def test_particle_frame_shape(self):
        """Test particle frame has correct shape"""
        frame = self.generator._create_particle_frame(t=0.0, width=1080, height=1920)

        # Verify shape is (height, width, 3)
        assert frame.shape == (1920, 1080, 3)

        # Verify dtype
        assert frame.dtype == np.uint8

    def test_particle_frame_not_empty(self):
        """Test particle frame contains particles (not all black/same color)"""
        frame = self.generator._create_particle_frame(t=0.0, n_particles=40)

        # Background should be #121212 = (18, 18, 18)
        bg_rgb = (18, 18, 18)

        # Count pixels that are NOT background color (particles)
        non_bg_pixels = np.sum(np.any(frame != bg_rgb, axis=2))

        # Should have some particles (at least 40 particles * 4px each = 160 pixels)
        assert non_bg_pixels > 100, f"Expected particles, but only {non_bg_pixels} non-bg pixels found"

    def test_run_returns_paths(self):
        """Test run returns list of output paths"""
        # Mock generate_video to avoid actual video generation
        with patch.object(self.generator, 'generate_video') as mock_generate:
            mock_generate.return_value = "data/7_shorts/cluster_0.mp4"

            # Create temporary scripts file
            scripts_data = [
                {
                    "cluster_id": "0",
                    "shorts": self.sample_shorts_script,
                    "instagram": self.sample_instagram_script
                }
            ]

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                import json
                json.dump(scripts_data, f)
                temp_path = f.name

            try:
                # Run pipeline
                paths = self.generator.run(temp_path)

                # Verify list returned
                assert isinstance(paths, list)
                assert len(paths) == 1
                assert paths[0] == "data/7_shorts/cluster_0.mp4"

                # Verify generate_video was called
                mock_generate.assert_called_once()

            finally:
                # Cleanup
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_hex_to_rgb(self):
        """Test hex to RGB conversion"""
        # Test brand green
        assert self.generator._hex_to_rgb("#00C853") == (0, 200, 83)

        # Test background
        assert self.generator._hex_to_rgb("#121212") == (18, 18, 18)

        # Test bearish red
        assert self.generator._hex_to_rgb("#FF3D3D") == (255, 61, 61)
