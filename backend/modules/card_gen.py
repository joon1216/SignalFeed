"""
SignalFeed Instagram Card Generator
Pillow 기반 1080x1080px 카드 이미지 생성 (Pexels 배경 + 새 레이아웃)
"""

import os
import sys
import json
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Add project root to path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.modules.image_fetcher import ImageFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CardGenerator:
    """Instagram 카드 이미지 생성기 (1080x1080px, Pexels 배경)"""

    # Canvas dimensions (Instagram square format)
    WIDTH = 1080
    HEIGHT = 1080

    # Layout constants
    LEFT_MARGIN = 60
    RIGHT_MARGIN = 60
    CONTENT_WIDTH = WIDTH - LEFT_MARGIN - RIGHT_MARGIN  # 960px

    # Signal colors
    COLORS = {
        "bg_dark": "#111111",
        "bg_surface": "#1A1A1A",
        "bg_card": "#2C2C2C",
        "bullish": "#00C853",
        "bearish": "#FF3D3D",
        "neutral": "#666666",
        "text_white": "#FAFAFA",
        "text_gray": "#A0A0A0",
        "text_dark_gray": "#555555",
        "separator": "#2C2C2C",
    }

    def __init__(self, font_path: str = "assets/fonts/NanumGothicBold.ttf"):
        """
        Initialize CardGenerator

        Args:
            font_path: Path to Korean font file
        """
        # Font loading priority list
        font_candidates = [
            font_path,
            os.path.expanduser("~/Library/Fonts/NanumGothic-Bold.ttf"),
            os.path.expanduser("~/Library/Fonts/NanumGothic-Regular.ttf"),
            "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        ]

        loaded_font = None
        for candidate in font_candidates:
            if os.path.exists(candidate):
                try:
                    # Font sizes for new layout
                    self.font_xxlarge = ImageFont.truetype(candidate, 72)
                    self.font_xlarge = ImageFont.truetype(candidate, 60)
                    self.font_large = ImageFont.truetype(candidate, 52)
                    self.font_mlarge = ImageFont.truetype(candidate, 40)
                    self.font_medium = ImageFont.truetype(candidate, 36)
                    self.font_msmall = ImageFont.truetype(candidate, 32)
                    self.font_small = ImageFont.truetype(candidate, 26)
                    self.font_xsmall = ImageFont.truetype(candidate, 24)
                    self.font_xxsmall = ImageFont.truetype(candidate, 22)
                    self.font_tiny = ImageFont.truetype(candidate, 20)
                    self.font_micro = ImageFont.truetype(candidate, 18)
                    logger.info(f"Loaded font: {candidate}")
                    loaded_font = candidate
                    break
                except Exception as e:
                    logger.debug(f"Failed to load {candidate}: {e}")
                    continue

        if not loaded_font:
            logger.warning("All font candidates failed. Using default font.")
            default = ImageFont.load_default()
            self.font_xxlarge = default
            self.font_xlarge = default
            self.font_large = default
            self.font_mlarge = default
            self.font_medium = default
            self.font_msmall = default
            self.font_small = default
            self.font_xsmall = default
            self.font_xxsmall = default
            self.font_tiny = default
            self.font_micro = default

        # Initialize ImageFetcher
        self.image_fetcher = ImageFetcher()

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_text_wrapped(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        xy: Tuple[int, int],
        font: ImageFont.FreeTypeFont,
        fill: str,
        max_width: int,
        max_lines: int = None,
        align: str = "left"
    ) -> int:
        """
        Draw text with word wrapping

        Returns:
            Height of drawn text
        """
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        # Limit lines
        if max_lines:
            lines = lines[:max_lines]

        # Draw lines
        x, y = xy
        total_height = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1]

            if align == "center":
                line_width = bbox[2] - bbox[0]
                x_offset = (max_width - line_width) // 2
                draw.text((x + x_offset, y), line, font=font, fill=fill)
            else:
                draw.text((x, y), line, font=font, fill=fill)

            y += line_height + 10
            total_height += line_height + 10

        return total_height

    def generate_slide1_cover(self, script: Dict, background: Image.Image) -> Image.Image:
        """
        SLIDE 1: Cover with Pexels background
        Hook-first design like @kiyominosekai
        """
        # Use provided background or create fallback
        image = background.copy() if background else Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(image)

        # Dark overlay gradient (top 20% transparent → bottom 80% opaque)
        overlay = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        for y in range(self.HEIGHT):
            alpha = int(min(255, (y / self.HEIGHT) * 255 * 0.75))
            overlay_draw.rectangle([(0, y), (self.WIDTH, y+1)], fill=(0, 0, 0, alpha))

        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)

        # Top-left: SIGNALFEED brand
        draw.text(
            (self.LEFT_MARGIN, 50),
            "SIGNALFEED",
            font=self.font_xsmall,
            fill=self.COLORS["text_white"]
        )

        # Center-bottom: Hook title
        hook_title = script.get("hook_title", script.get("title", "경제 뉴스"))
        y_hook = 600
        self._draw_text_wrapped(
            draw, hook_title,
            (self.LEFT_MARGIN, y_hook),
            self.font_xxlarge,
            self.COLORS["text_white"],
            self.CONTENT_WIDTH,
            max_lines=2,
            align="left"
        )

        # Signal badge below title
        signal = script.get("signal", "neutral")
        signal_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}[signal]
        signal_text = {"bullish": "호재", "bearish": "악재", "neutral": "중립"}[signal]
        signal_color = self.COLORS.get(signal, self.COLORS["neutral"])

        badge_text = f"{signal_emoji} {signal_text}"
        bbox = draw.textbbox((0, 0), badge_text, font=self.font_medium)
        badge_width = bbox[2] - bbox[0] + 40
        badge_height = 50
        badge_x = self.LEFT_MARGIN
        badge_y = 800

        # Draw pill-shaped badge
        draw.rounded_rectangle(
            [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
            radius=25,
            fill=signal_color
        )
        draw.text(
            (badge_x + 20, badge_y + 10),
            badge_text,
            font=self.font_medium,
            fill=self.COLORS["text_white"]
        )

        # Source line
        sources = script.get("sources", ["Reuters", "Bloomberg", "FT"])
        source_text = " · ".join(sources[:3])
        draw.text(
            (self.LEFT_MARGIN, 900),
            source_text,
            font=self.font_micro,
            fill=self.COLORS["text_gray"]
        )

        # Bottom green line accent
        draw.rectangle(
            [(0, 1060), (self.WIDTH, 1063)],
            fill=self.COLORS["bullish"]
        )

        # Hashtag badges bottom-right
        hashtags = ["#경제", "#투자"]
        hashtag_x = self.WIDTH - 200
        hashtag_y = 1000

        for hashtag in hashtags:
            bbox = draw.textbbox((0, 0), hashtag, font=self.font_tiny)
            tag_width = bbox[2] - bbox[0] + 20
            tag_height = 30

            draw.rounded_rectangle(
                [(hashtag_x, hashtag_y), (hashtag_x + tag_width, hashtag_y + tag_height)],
                radius=15,
                fill=self.COLORS["bg_card"]
            )
            draw.text(
                (hashtag_x + 10, hashtag_y + 5),
                hashtag,
                font=self.font_tiny,
                fill=self.COLORS["text_gray"]
            )

            hashtag_x += tag_width + 10

        return image

    def generate_slide_sector(
        self,
        slide_num: int,
        label: str,
        signal: str,
        sectors: List[Dict],
        fact: str
    ) -> Image.Image:
        """
        SLIDES 2-4: Sector cards (호재/악재/중립)
        Clean editorial dark bg layout
        """
        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(image)

        signal_color = self.COLORS.get(signal, self.COLORS["neutral"])

        # Top-left: SIGNALFEED micro brand
        draw.text(
            (self.LEFT_MARGIN, 50),
            "SIGNALFEED",
            font=self.font_tiny,
            fill=self.COLORS["bullish"]
        )

        # Slide number indicator top-right
        draw.text(
            (self.WIDTH - self.RIGHT_MARGIN - 50, 50),
            f"{slide_num}/5",
            font=self.font_micro,
            fill=self.COLORS["text_gray"]
        )

        # Section label with vertical bar
        bar_width = 4
        bar_height = 60
        draw.rectangle(
            [(self.LEFT_MARGIN, 100), (self.LEFT_MARGIN + bar_width, 100 + bar_height)],
            fill=signal_color
        )
        draw.text(
            (self.LEFT_MARGIN + bar_width + 20, 110),
            label,
            font=self.font_mlarge,
            fill=signal_color
        )

        # Sector items
        y_sectors = 200
        for sector in sectors:
            sector_name = sector.get("name", "")
            sector_reason = sector.get("reason", "")

            # Sector name
            draw.text(
                (self.LEFT_MARGIN, y_sectors),
                sector_name,
                font=self.font_large,
                fill=signal_color
            )

            # Reason text (indented)
            y_sectors += 60
            self._draw_text_wrapped(
                draw, sector_reason,
                (self.LEFT_MARGIN + 20, y_sectors),
                self.font_small,
                self.COLORS["text_gray"],
                self.CONTENT_WIDTH - 20,
                max_lines=2
            )

            y_sectors += 100

        # Bottom fact box
        y_fact = 880

        # Separator line
        draw.rectangle(
            [(0, y_fact), (self.WIDTH, y_fact + 1)],
            fill=self.COLORS["separator"]
        )

        # FACT label
        draw.text(
            (self.LEFT_MARGIN, y_fact + 20),
            "FACT /",
            font=self.font_tiny,
            fill=self.COLORS["text_dark_gray"]
        )

        # Fact text
        self._draw_text_wrapped(
            draw, fact,
            (self.LEFT_MARGIN, y_fact + 50),
            self.font_xxsmall,
            self.COLORS["text_gray"],
            self.CONTENT_WIDTH,
            max_lines=3
        )

        return image

    def generate_slide5_conclusion(self, script: Dict) -> Image.Image:
        """
        SLIDE 5: Conclusion with CTA
        """
        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(image)

        # Top-left: SIGNALFEED micro brand
        draw.text(
            (self.LEFT_MARGIN, 50),
            "SIGNALFEED",
            font=self.font_tiny,
            fill=self.COLORS["bullish"]
        )

        # "오늘의 결론" heading
        draw.text(
            (self.LEFT_MARGIN, 120),
            "오늘의 결론",
            font=self.font_xlarge,
            fill=self.COLORS["text_white"]
        )

        # Summary rows with colored dots
        summaries = [
            {"color": self.COLORS["bullish"], "text": script.get("slide5", {}).get("summary1", "")},
            {"color": self.COLORS["bearish"], "text": script.get("slide5", {}).get("summary2", "")},
            {"color": self.COLORS["neutral"], "text": script.get("slide5", {}).get("summary3", "")}
        ]

        y_summary = 230
        for summary in summaries:
            if not summary["text"]:
                continue

            # Colored dot
            dot_radius = 5
            draw.ellipse(
                [(self.LEFT_MARGIN, y_summary + 10), (self.LEFT_MARGIN + dot_radius * 2, y_summary + 10 + dot_radius * 2)],
                fill=summary["color"]
            )

            # Summary text
            self._draw_text_wrapped(
                draw, summary["text"],
                (self.LEFT_MARGIN + 30, y_summary),
                self.font_msmall,
                self.COLORS["text_white"],
                self.CONTENT_WIDTH - 30,
                max_lines=2
            )

            y_summary += 80

        # CTA block
        y_cta = 750

        # Separator line
        draw.rectangle(
            [(0, y_cta), (self.WIDTH, y_cta + 1)],
            fill=self.COLORS["separator"]
        )

        # Main CTA
        cta_main = "더 궁금하다면 댓글에 '분석' 남겨주세요"
        draw.text(
            (self.LEFT_MARGIN, y_cta + 40),
            cta_main,
            font=self.font_msmall,
            fill=self.COLORS["text_white"]
        )

        # Sub CTA
        cta_sub = "→ 상세 리포트 DM으로 드립니다"
        draw.text(
            (self.LEFT_MARGIN, y_cta + 100),
            cta_sub,
            font=self.font_small,
            fill=self.COLORS["bullish"]
        )

        # Disclaimer
        disclaimer = "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
        bbox = draw.textbbox((0, 0), disclaimer, font=self.font_micro)
        disclaimer_width = bbox[2] - bbox[0]
        disclaimer_x = (self.WIDTH - disclaimer_width) // 2

        draw.text(
            (disclaimer_x, 980),
            disclaimer,
            font=self.font_micro,
            fill=self.COLORS["text_dark_gray"]
        )

        return image

    def generate_slide5_conclusion_new(self, slide_data: Dict) -> Image.Image:
        """
        SLIDE 5: Conclusion with watch_point (new structure)
        """
        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(image)

        # Top-left: SIGNALFEED micro brand
        draw.text(
            (self.LEFT_MARGIN, 50),
            "SIGNALFEED",
            font=self.font_tiny,
            fill=self.COLORS["bullish"]
        )

        # "오늘의 결론" heading
        title = slide_data.get("title", "오늘의 결론")
        draw.text(
            (self.LEFT_MARGIN, 120),
            title,
            font=self.font_xlarge,
            fill=self.COLORS["text_white"]
        )

        # Summary rows with colored dots
        summaries = slide_data.get("summaries", [])
        y_summary = 230

        for summary in summaries:
            signal = summary.get("signal", "neutral")
            text = summary.get("text", "")
            dot_color = self.COLORS.get(signal, self.COLORS["neutral"])

            # Colored dot
            dot_radius = 5
            draw.ellipse(
                [(self.LEFT_MARGIN, y_summary + 10), (self.LEFT_MARGIN + dot_radius * 2, y_summary + 10 + dot_radius * 2)],
                fill=dot_color
            )

            # Summary text
            self._draw_text_wrapped(
                draw, text,
                (self.LEFT_MARGIN + 30, y_summary),
                self.font_msmall,
                self.COLORS["text_white"],
                self.CONTENT_WIDTH - 30,
                max_lines=2
            )

            y_summary += 80

        # Watch point (new)
        watch_point = slide_data.get("watch_point", "")
        if watch_point:
            y_watch = 550

            # Green box background
            draw.rounded_rectangle(
                [(self.LEFT_MARGIN, y_watch), (self.WIDTH - self.RIGHT_MARGIN, y_watch + 100)],
                radius=10,
                fill=self.COLORS["bg_card"]
            )

            # "주목 포인트" label
            draw.text(
                (self.LEFT_MARGIN + 20, y_watch + 15),
                "주목 포인트",
                font=self.font_xxsmall,
                fill=self.COLORS["bullish"]
            )

            # Watch point text
            self._draw_text_wrapped(
                draw, watch_point,
                (self.LEFT_MARGIN + 20, y_watch + 50),
                self.font_small,
                self.COLORS["text_white"],
                self.CONTENT_WIDTH - 40,
                max_lines=2
            )

        # CTA block
        y_cta = 700

        # Separator line
        draw.rectangle(
            [(0, y_cta), (self.WIDTH, y_cta + 1)],
            fill=self.COLORS["separator"]
        )

        # Main CTA
        cta_main = slide_data.get("cta", "더 궁금하다면 댓글에 '분석' 남겨주세요")
        draw.text(
            (self.LEFT_MARGIN, y_cta + 40),
            cta_main,
            font=self.font_msmall,
            fill=self.COLORS["text_white"]
        )

        # Sub CTA
        cta_sub = slide_data.get("cta_sub", "→ 상세 리포트 DM으로 드립니다")
        draw.text(
            (self.LEFT_MARGIN, y_cta + 100),
            cta_sub,
            font=self.font_small,
            fill=self.COLORS["bullish"]
        )

        # Disclaimer
        disclaimer = "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
        bbox = draw.textbbox((0, 0), disclaimer, font=self.font_micro)
        disclaimer_width = bbox[2] - bbox[0]
        disclaimer_x = (self.WIDTH - disclaimer_width) // 2

        draw.text(
            (disclaimer_x, 980),
            disclaimer,
            font=self.font_micro,
            fill=self.COLORS["text_dark_gray"]
        )

        return image

    def generate_slide2_context(self, slide_data: Dict) -> Image.Image:
        """
        SLIDE 2: Context (무슨 일이?)
        3 fact bullets
        """
        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(image)

        # Top-left: SIGNALFEED micro brand
        draw.text(
            (self.LEFT_MARGIN, 50),
            "SIGNALFEED",
            font=self.font_tiny,
            fill=self.COLORS["bullish"]
        )

        # Slide number indicator top-right
        draw.text(
            (self.WIDTH - self.RIGHT_MARGIN - 50, 50),
            "2/5",
            font=self.font_micro,
            fill=self.COLORS["text_gray"]
        )

        # Title
        title = slide_data.get("title", "무슨 일이?")
        draw.text(
            (self.LEFT_MARGIN, 120),
            title,
            font=self.font_msmall,
            fill=self.COLORS["text_gray"]
        )

        # Facts as bullet points
        facts = slide_data.get("facts", [])
        y_facts = 200

        for fact in facts:
            # Dash prefix
            draw.text(
                (self.LEFT_MARGIN, y_facts),
                "—",
                font=self.font_small,
                fill=self.COLORS["text_white"]
            )

            # Fact text
            self._draw_text_wrapped(
                draw, fact,
                (self.LEFT_MARGIN + 30, y_facts),
                self.font_small,
                self.COLORS["text_white"],
                self.CONTENT_WIDTH - 30,
                max_lines=2
            )

            y_facts += 120

        # Source attribution at bottom
        source = slide_data.get("source", "")
        if source:
            draw.text(
                (self.LEFT_MARGIN, 950),
                f"출처: {source}",
                font=self.font_micro,
                fill=self.COLORS["text_gray"]
            )

        return image

    def generate_all_slides(self, script: Dict) -> List[Image.Image]:
        """
        Generate all 5 slides for Instagram carousel (new structure)

        Args:
            script: Instagram script from content_gen.py

        Returns:
            List of PIL Image objects (5 slides)
        """
        logger.info(f"Generating slides for cluster {script.get('cluster_id', 'unknown')}")

        # Fetch background image for slide 1 using pexels_keyword
        pexels_keyword = script.get("pexels_keyword", "financial district skyscraper aerial")
        background = self.image_fetcher.fetch_image(pexels_keyword)
        if not background:
            background = self.image_fetcher._create_fallback_background()

        slides_data = script.get("slides", [])
        generated_slides = []

        for slide_data in slides_data:
            slide_type = slide_data.get("type")

            if slide_type == "cover":
                generated_slides.append(self.generate_slide1_cover(script, background))

            elif slide_type == "context":
                generated_slides.append(self.generate_slide2_context(slide_data))

            elif slide_type == "bullish":
                sectors = slide_data.get("sectors", [])
                fact = slide_data.get("fact", "")
                generated_slides.append(self.generate_slide_sector(
                    3, "호재", "bullish", sectors, fact
                ))

            elif slide_type == "bearish":
                sectors = slide_data.get("sectors", [])
                fact = slide_data.get("fact", "")
                generated_slides.append(self.generate_slide_sector(
                    4, "악재", "bearish", sectors, fact
                ))

            elif slide_type == "conclusion":
                generated_slides.append(self.generate_slide5_conclusion_new(slide_data))

        logger.info(f"✅ Generated {len(generated_slides)} slides")
        return generated_slides

    def save_slides(self, slides: List[Image.Image], cluster_id: str) -> List[str]:
        """
        Save slides to disk

        Args:
            slides: List of PIL Image objects
            cluster_id: Cluster ID for directory naming

        Returns:
            List of file paths
        """
        output_dir = f"data/6_cards/cluster_{cluster_id}"
        os.makedirs(output_dir, exist_ok=True)

        paths = []
        for i, slide in enumerate(slides, start=1):
            path = f"{output_dir}/slide_{i}.png"
            slide.save(path, "PNG")
            paths.append(path)
            logger.info(f"Saved: {path}")

        return paths

    def run(self, input_path: str = "data/5_generated/scripts.json") -> None:
        """
        Full pipeline: load scripts → generate slides → save

        Args:
            input_path: Path to scripts.json
        """
        logger.info(f"\n{'='*70}")
        logger.info("6️⃣ Instagram Card Generation")
        logger.info(f"{'='*70}")

        with open(input_path, 'r', encoding='utf-8') as f:
            scripts = json.load(f)

        for script_data in scripts:
            instagram_script = script_data.get("instagram", {})
            slides = self.generate_all_slides(instagram_script)
            paths = self.save_slides(slides, instagram_script.get("cluster_id", "unknown"))
            logger.info(f"✅ Cluster {instagram_script.get('cluster_id')}: {len(paths)}장 생성")

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ Card generation complete!")
        logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    generator = CardGenerator()
    generator.run()
