"""
SignalFeed YouTube Shorts Generator
MoviePy + gTTS 기반 1080x1920px 세로 영상 생성
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoClip, TextClip, CompositeVideoClip, AudioFileClip,
    concatenate_videoclips, ImageClip
)
from gtts import gTTS

# Add project root to path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from assets.colors import COLORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ShortsGenerator:
    """YouTube Shorts 영상 생성기"""

    # Video specs
    WIDTH = 1080
    HEIGHT = 1920
    FPS = 30
    DURATION = 60  # seconds

    def __init__(self, font_path: str = "assets/fonts/NanumGothicBold.ttf"):
        """
        Initialize ShortsGenerator

        Args:
            font_path: Path to Korean font file
        """
        self.font_path = font_path

        # Create temp directory
        self.temp_dir = "data/7_shorts/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """
        Convert hex color to RGB tuple

        Args:
            hex_color: Hex color string (#RRGGBB)

        Returns:
            RGB tuple (r, g, b)
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _create_particle_frame(self, t: float, width: int = 1080, height: int = 1920,
                               n_particles: int = 40, bg_color: str = "#121212") -> np.ndarray:
        """
        Create particle animation frame

        Args:
            t: Time in seconds
            width: Frame width
            height: Frame height
            n_particles: Number of particles
            bg_color: Background color (hex)

        Returns:
            Numpy array (height, width, 3)
        """
        # Create dark background
        bg_rgb = self._hex_to_rgb(bg_color)
        frame = np.full((height, width, 3), bg_rgb, dtype=np.uint8)

        # Draw particles
        particle_color = (51, 51, 51)  # #333333

        for i in range(n_particles):
            # Particle base position (pseudo-random but deterministic)
            x0 = (i * 137) % width
            y0 = (i * 211) % height

            # Animated movement
            phase = i * 0.5
            speed = 0.3
            amplitude_x = 50
            amplitude_y = 50

            x = int(x0 + np.sin(t * speed + phase) * amplitude_x) % width
            y = int(y0 + np.cos(t * speed + phase) * amplitude_y) % height

            # Particle size (2-4px)
            size = 2 + (i % 3)

            # Draw particle as small circle
            for dx in range(-size, size + 1):
                for dy in range(-size, size + 1):
                    if dx*dx + dy*dy <= size*size:
                        px = x + dx
                        py = y + dy
                        if 0 <= px < width and 0 <= py < height:
                            frame[py, px] = particle_color

        return frame

    def generate_narration(self, script: Dict) -> str:
        """
        Generate Korean narration audio using gTTS

        Args:
            script: Shorts script dict with narration field

        Returns:
            Path to generated MP3 file
        """
        cluster_id = script.get("cluster_id", "0")
        narration_text = script.get("narration", "")

        logger.info(f"Generating narration for cluster {cluster_id}...")

        # Generate TTS
        tts = gTTS(text=narration_text, lang='ko', slow=False)

        # Save to temp file
        output_path = os.path.join(self.temp_dir, f"narration_{cluster_id}.mp3")
        tts.save(output_path)

        logger.info(f"Narration saved to {output_path}")
        return output_path

    def generate_video(self, script: Dict, instagram_script: Dict) -> str:
        """
        Generate YouTube Shorts video

        Args:
            script: Shorts script dict
            instagram_script: Instagram script dict (for visual data)

        Returns:
            Path to generated MP4 file
        """
        cluster_id = str(script.get("cluster_id", "0"))
        signal = instagram_script.get("signal", "neutral")

        logger.info(f"Generating video for cluster {cluster_id}...")

        # Create particle background clip (60 seconds)
        bg_clip = VideoClip(
            lambda t: self._create_particle_frame(t, bg_color=COLORS["bg"]),
            duration=self.DURATION
        )

        # Intro section (0-3s): Brand text
        intro_text = TextClip(
            "SIGNALFEED",
            fontsize=60,
            color='white',
            font=self.font_path,
            size=(self.WIDTH, None),
            method='caption'
        ).set_position('center').set_start(0).set_duration(3).crossfadein(0.5)

        intro_subtitle = TextClip(
            "오늘의 글로벌 경제 시그널",
            fontsize=28,
            color='gray',
            font=self.font_path,
            size=(self.WIDTH - 100, None),
            method='caption'
        ).set_position(('center', 800)).set_start(0.5).set_duration(2.5).crossfadein(0.3)

        # Issue title section (3-11s)
        issue_title = instagram_script["slides"][0]["title"]
        signal_emoji = instagram_script["slides"][0].get("signal_emoji", "⚪")

        title_text = TextClip(
            issue_title[:50],  # Max 50 chars
            fontsize=52,
            color='white',
            font=self.font_path,
            size=(self.WIDTH - 100, None),
            method='caption'
        ).set_position('center').set_start(3).set_duration(8).crossfadein(0.5)

        signal_badge = TextClip(
            f"{signal_emoji} {signal.upper()}",
            fontsize=36,
            color=self._hex_to_rgb(COLORS["bullish"] if signal == "bullish" else
                                   COLORS["bearish"] if signal == "bearish" else
                                   COLORS["neutral"]),
            font=self.font_path
        ).set_position(('center', 700)).set_start(4).set_duration(7).crossfadein(0.3)

        # Sources chip
        sources_text = TextClip(
            "Reuters · Bloomberg · FT",
            fontsize=20,
            color='gray',
            font=self.font_path
        ).set_position(('center', 900)).set_start(5).set_duration(6)

        # Bullish section (11-23s) - simplified
        bullish_label = TextClip(
            "🟢 호재",
            fontsize=48,
            color=self._hex_to_rgb(COLORS["bullish"]),
            font=self.font_path
        ).set_position((60, 400)).set_start(11).set_duration(12).crossfadein(0.3)

        bullish_text = TextClip(
            "금리 인하로 성장 섹터 수혜\nTech · Real Estate · 소비재",
            fontsize=28,
            color='white',
            font=self.font_path,
            size=(self.WIDTH - 120, None),
            method='caption'
        ).set_position((60, 550)).set_start(12).set_duration(11).crossfadein(0.5)

        # Bearish section (23-35s) - simplified
        bearish_label = TextClip(
            "🔴 악재",
            fontsize=48,
            color=self._hex_to_rgb(COLORS["bearish"]),
            font=self.font_path
        ).set_position((60, 400)).set_start(23).set_duration(12).crossfadein(0.3)

        bearish_text = TextClip(
            "인플레이션 압력 지속\n소비 · 에너지 부담 증가",
            fontsize=28,
            color='white',
            font=self.font_path,
            size=(self.WIDTH - 120, None),
            method='caption'
        ).set_position((60, 550)).set_start(24).set_duration(11).crossfadein(0.5)

        # Key fact (35-43s)
        fact_label = TextClip(
            "핵심 팩트",
            fontsize=32,
            color=self._hex_to_rgb(COLORS["brand"]),
            font=self.font_path
        ).set_position((60, 400)).set_start(35).set_duration(8).crossfadein(0.3)

        fact_text = TextClip(
            "글로벌 경제 변화가\n투자 환경에 영향을 줄 것으로 보입니다",
            fontsize=28,
            color='white',
            font=self.font_path,
            size=(self.WIDTH - 120, None),
            method='caption'
        ).set_position((60, 520)).set_start(36).set_duration(7).crossfadein(0.5)

        # Conclusion (43-53s)
        conclusion_text = TextClip(
            f"{signal.upper()} 시그널\n\n자세한 분석은\n프로필 링크에서",
            fontsize=36,
            color='white',
            font=self.font_path,
            size=(self.WIDTH - 120, None),
            method='caption',
            align='center'
        ).set_position('center').set_start(43).set_duration(10).crossfadein(0.5)

        # Outro (53-60s)
        outro_logo = TextClip(
            "SIGNALFEED",
            fontsize=54,
            color=self._hex_to_rgb(COLORS["brand"]),
            font=self.font_path
        ).set_position('center').set_start(53).set_duration(7).crossfadein(0.5)

        outro_cta = TextClip(
            "구독과 좋아요 부탁드립니다 🙏",
            fontsize=28,
            color='white',
            font=self.font_path
        ).set_position(('center', 800)).set_start(54).set_duration(6).crossfadein(0.3)

        disclaimer_text = TextClip(
            "본 콘텐츠는 AI 분석 정보이며\n투자 권유가 아닙니다",
            fontsize=18,
            color='gray',
            font=self.font_path,
            size=(self.WIDTH - 100, None),
            method='caption',
            align='center'
        ).set_position(('center', 1000)).set_start(54.5).set_duration(5.5)

        # Composite all clips
        video = CompositeVideoClip([
            bg_clip,
            intro_text, intro_subtitle,
            title_text, signal_badge, sources_text,
            bullish_label, bullish_text,
            bearish_label, bearish_text,
            fact_label, fact_text,
            conclusion_text,
            outro_logo, outro_cta, disclaimer_text
        ], size=(self.WIDTH, self.HEIGHT))

        # Generate narration audio
        narration_path = self.generate_narration(script)
        audio = AudioFileClip(narration_path)

        # Set audio (cut to video duration if longer)
        if audio.duration > video.duration:
            audio = audio.subclip(0, video.duration)
        video = video.set_audio(audio)

        # Export video
        output_dir = "data/7_shorts"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"cluster_{cluster_id}.mp4")

        logger.info(f"Exporting video to {output_path}...")

        # Write video file with containsSyntheticMedia flag in metadata
        video.write_videofile(
            output_path,
            fps=self.FPS,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            ffmpeg_params=[
                '-metadata', 'containsSyntheticMedia=true',
                '-metadata', 'comment=AI-generated content (gTTS + MoviePy)'
            ]
        )

        logger.info(f"Video exported to {output_path}")

        # Cleanup
        video.close()
        audio.close()

        return output_path

    def run(self, scripts_path: str = "data/5_generated/scripts.json") -> List[str]:
        """
        Full pipeline: load scripts → generate videos → return paths

        Args:
            scripts_path: Input scripts JSON path

        Returns:
            List of output video paths
        """
        logger.info("=" * 70)
        logger.info("SignalFeed Shorts Generator Started")
        logger.info("=" * 70)

        # Load scripts
        logger.info(f"Loading scripts from {scripts_path}...")
        with open(scripts_path, 'r', encoding='utf-8') as f:
            scripts_data = json.load(f)

        logger.info(f"Loaded {len(scripts_data)} scripts")

        # Generate videos
        output_paths = []

        for item in scripts_data:
            try:
                shorts_script = item.get("shorts", {})
                instagram_script = item.get("instagram", {})

                # Generate video
                video_path = self.generate_video(shorts_script, instagram_script)
                output_paths.append(video_path)

            except Exception as e:
                logger.error(f"Error generating video for cluster {item.get('cluster_id')}: {e}")
                continue

        logger.info("=" * 70)
        logger.info(f"Shorts Generation Complete: {len(output_paths)} videos")
        logger.info("=" * 70)

        return output_paths


if __name__ == "__main__":
    # Test run
    generator = ShortsGenerator()

    # Use sample data if exists
    sample_path = "data/5_generated/scripts.json"
    if os.path.exists(sample_path):
        paths = generator.run(sample_path)
        logger.info(f"Generated {len(paths)} videos")
    else:
        logger.warning(f"Sample data not found at {sample_path}")
