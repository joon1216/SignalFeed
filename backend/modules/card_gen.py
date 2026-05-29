"""
SignalFeed Instagram Card Generator
Pillow 기반 1080x1920px 다크모드 카드 이미지 생성 (전면 개편 레이아웃)
"""

import os
import sys
import json
import logging
from typing import List, Dict, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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


class CardGenerator:
    """Instagram 카드 이미지 생성기 (전면 개편 레이아웃)"""

    # Canvas dimensions (Instagram Story/Reels ratio)
    WIDTH = 1080
    HEIGHT = 1920

    # Layout constants
    LEFT_MARGIN = 60
    RIGHT_MARGIN = 60
    CONTENT_WIDTH = WIDTH - LEFT_MARGIN - RIGHT_MARGIN  # 960px

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
                    # Updated font sizes for new layout
                    self.font_xxlarge = ImageFont.truetype(candidate, 52)
                    self.font_xlarge = ImageFont.truetype(candidate, 44)
                    self.font_large = ImageFont.truetype(candidate, 40)
                    self.font_mlarge = ImageFont.truetype(candidate, 36)
                    self.font_medium = ImageFont.truetype(candidate, 32)
                    self.font_msmall = ImageFont.truetype(candidate, 28)
                    self.font_small = ImageFont.truetype(candidate, 24)
                    self.font_xsmall = ImageFont.truetype(candidate, 22)
                    self.font_tiny = ImageFont.truetype(candidate, 20)
                    logger.info(f"Loaded font: {candidate}")
                    loaded_font = candidate
                    break
                except Exception as e:
                    logger.debug(f"Failed to load {candidate}: {e}")
                    continue

        if not loaded_font:
            logger.warning("All font candidates failed. Using default font.")
            self.font_xxlarge = ImageFont.load_default()
            self.font_xlarge = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_mlarge = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_msmall = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_xsmall = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple (supports color names)"""
        # Convert color names to hex
        color_names = {
            "white": "#FFFFFF",
            "black": "#000000",
            "red": "#FF0000",
            "green": "#00FF00",
            "blue": "#0000FF"
        }

        if hex_color in color_names:
            hex_color = color_names[hex_color]

        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_rounded_rect(self, draw: ImageDraw.ImageDraw, xy: Tuple[int, int, int, int],
                          radius: int, fill: str, outline: str = None, width: int = 2):
        """Draw rounded rectangle"""
        x1, y1, x2, y2 = xy
        fill_rgb = self._hex_to_rgb(fill) if fill else None
        outline_rgb = self._hex_to_rgb(outline) if outline else None

        draw.rounded_rectangle(
            xy=(x1, y1, x2, y2),
            radius=radius,
            fill=fill_rgb,
            outline=outline_rgb,
            width=width
        )

    def _draw_text_wrapped(self, draw: ImageDraw.ImageDraw, text: str, xy: Tuple[int, int],
                          font: ImageFont.FreeTypeFont, fill: str, max_width: int,
                          align: str = "left", line_spacing: int = 10) -> int:
        """
        Draw text with word wrapping

        Returns:
            Height of drawn text block
        """
        # Convert color name to hex if needed
        if fill == "white":
            fill = "#FFFFFF"
        elif fill == "black":
            fill = "#000000"

        fill_rgb = self._hex_to_rgb(fill)
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        x, y = xy
        total_height = 0

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]

            if align == "center":
                draw.text((x + (max_width - line_width) // 2, y), line, font=font, fill=fill_rgb)
            elif align == "right":
                draw.text((x + max_width - line_width, y), line, font=font, fill=fill_rgb)
            else:
                draw.text((x, y), line, font=font, fill=fill_rgb)

            y += line_height + line_spacing
            total_height += line_height + line_spacing

        return total_height

    def generate_slide1_cover(self, script: Dict) -> Image.Image:
        """
        Generate Slide 1 (Cover)

        Layout:
        - y=60: SIGNALFEED brand (green, 28px)
        - y=160: live dot + "오늘의 핵심 이슈" (gray, 24px)
        - y=320: issue title (white, 52px bold, center, max 2 lines)
        - y=600: signal badge large (emoji + text, 36px, center)
        - y=800: source chips (Reuters · Bloomberg · FT, gray, 22px, center)
        - y=900: "슬라이드로 자세히 보기 →" (green, 24px, center)
        - y=1860: green line accent (bottom)
        """
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        # y=60: SIGNALFEED brand
        draw.text((self.LEFT_MARGIN, 60), "SIGNALFEED", font=self.font_msmall, fill=self._hex_to_rgb(COLORS["brand"]))

        # y=160: live dot + "오늘의 핵심 이슈"
        draw.ellipse((self.LEFT_MARGIN, 168, self.LEFT_MARGIN + 12, 180), fill=self._hex_to_rgb(COLORS["brand"]))
        draw.text((self.LEFT_MARGIN + 24, 160), "오늘의 핵심 이슈", font=self.font_small, fill=self._hex_to_rgb("#888888"))

        # y=320: issue title (center, max 2 lines)
        title = script["slides"][0]["title"]
        self._draw_text_wrapped(
            draw, title, (self.LEFT_MARGIN, 320),
            self.font_xxlarge, "white", self.CONTENT_WIDTH,
            align="center", line_spacing=20
        )

        # y=600: signal badge (emoji + text, center)
        signal_emoji = script["slides"][0].get("signal_emoji", "⚪")
        signal_text = script["slides"][0].get("body", "").split("\n")[0]  # First line
        badge_text = f"{signal_emoji} {signal_text}"

        bbox = draw.textbbox((0, 0), badge_text, font=self.font_mlarge)
        badge_width = bbox[2] - bbox[0]
        badge_x = (self.WIDTH - badge_width) // 2

        draw.text((badge_x, 600), badge_text, font=self.font_mlarge, fill=self._hex_to_rgb("white"))

        # y=800: source chips (center)
        sources = "Reuters · Bloomberg · FT"
        bbox = draw.textbbox((0, 0), sources, font=self.font_xsmall)
        sources_width = bbox[2] - bbox[0]
        sources_x = (self.WIDTH - sources_width) // 2

        draw.text((sources_x, 800), sources, font=self.font_xsmall, fill=self._hex_to_rgb("#888888"))

        # y=900: CTA text (center)
        cta = "슬라이드로 자세히 보기 →"
        bbox = draw.textbbox((0, 0), cta, font=self.font_small)
        cta_width = bbox[2] - bbox[0]
        cta_x = (self.WIDTH - cta_width) // 2

        draw.text((cta_x, 900), cta, font=self.font_small, fill=self._hex_to_rgb(COLORS["brand"]))

        # y=1860: green line accent
        draw.rectangle((self.LEFT_MARGIN, 1860, self.WIDTH - self.RIGHT_MARGIN, 1870), fill=self._hex_to_rgb(COLORS["brand"]))

        return img

    def generate_slide2_bullish(self, script: Dict) -> Image.Image:
        """Generate Slide 2 (Bullish) with new layout"""
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        slide_data = script["slides"][1]

        # y=60: label bar + label text
        bar_color = COLORS["bullish"]
        draw.rectangle((self.LEFT_MARGIN, 60, self.LEFT_MARGIN + 16, 120), fill=self._hex_to_rgb(bar_color))
        draw.text((self.LEFT_MARGIN + 36, 65), "호재", font=self.font_large, fill=self._hex_to_rgb("white"))

        # y=200: sector cards
        sectors = slide_data.get("sectors", [])
        body = slide_data.get("body", "")

        y_offset = 200
        for sector in sectors[:3]:  # Max 3 sectors
            # Sector card (160px tall, rounded corners)
            card_y1 = y_offset
            card_y2 = y_offset + 160

            # Dark green background
            self._draw_rounded_rect(
                draw,
                (self.LEFT_MARGIN, card_y1, self.WIDTH - self.RIGHT_MARGIN, card_y2),
                radius=20,
                fill="#0D3B2E"  # Dark green
            )

            # Sector name (green, 32px bold)
            draw.text((self.LEFT_MARGIN + 30, card_y1 + 30), sector, font=self.font_medium, fill=self._hex_to_rgb(COLORS["bullish"]))

            # Reason text (white, 26px, 2 lines max)
            reason_y = card_y1 + 80
            self._draw_text_wrapped(
                draw, body[:60], (self.LEFT_MARGIN + 30, reason_y),
                self.font_msmall, "white", self.CONTENT_WIDTH - 60,
                line_spacing=10
            )

            y_offset += 180  # 160px card + 20px spacing

        # y=1600: fact box
        fact_y1 = 1600
        fact_y2 = 1800

        self._draw_rounded_rect(
            draw,
            (self.LEFT_MARGIN, fact_y1, self.WIDTH - self.RIGHT_MARGIN, fact_y2),
            radius=20,
            fill="#1A1A1A"  # Darker bg
        )

        # "핵심 팩트" label
        draw.text((self.LEFT_MARGIN + 30, fact_y1 + 20), "핵심 팩트", font=self.font_xsmall, fill=self._hex_to_rgb("#888888"))

        # Fact text
        self._draw_text_wrapped(
            draw, body[:100], (self.LEFT_MARGIN + 30, fact_y1 + 60),
            self.font_msmall, "white", self.CONTENT_WIDTH - 60,
            line_spacing=10
        )

        return img

    def generate_slide3_bearish(self, script: Dict) -> Image.Image:
        """Generate Slide 3 (Bearish) - same structure as slide 2 but red theme"""
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        slide_data = script["slides"][2]

        # y=60: label bar + label text (red)
        bar_color = COLORS["bearish"]
        draw.rectangle((self.LEFT_MARGIN, 60, self.LEFT_MARGIN + 16, 120), fill=self._hex_to_rgb(bar_color))
        draw.text((self.LEFT_MARGIN + 36, 65), "악재", font=self.font_large, fill=self._hex_to_rgb("white"))

        # y=200: sector cards
        sectors = slide_data.get("sectors", [])
        body = slide_data.get("body", "")

        y_offset = 200
        for sector in sectors[:3]:
            card_y1 = y_offset
            card_y2 = y_offset + 160

            # Dark red background
            self._draw_rounded_rect(
                draw,
                (self.LEFT_MARGIN, card_y1, self.WIDTH - self.RIGHT_MARGIN, card_y2),
                radius=20,
                fill="#3B0D0D"  # Dark red
            )

            # Sector name (red, 32px bold)
            draw.text((self.LEFT_MARGIN + 30, card_y1 + 30), sector, font=self.font_medium, fill=self._hex_to_rgb(COLORS["bearish"]))

            # Reason text
            reason_y = card_y1 + 80
            self._draw_text_wrapped(
                draw, body[:60], (self.LEFT_MARGIN + 30, reason_y),
                self.font_msmall, "white", self.CONTENT_WIDTH - 60,
                line_spacing=10
            )

            y_offset += 180

        # y=1600: fact box
        fact_y1 = 1600
        fact_y2 = 1800

        self._draw_rounded_rect(
            draw,
            (self.LEFT_MARGIN, fact_y1, self.WIDTH - self.RIGHT_MARGIN, fact_y2),
            radius=20,
            fill="#1A1A1A"
        )

        draw.text((self.LEFT_MARGIN + 30, fact_y1 + 20), "핵심 팩트", font=self.font_xsmall, fill=self._hex_to_rgb("#888888"))

        self._draw_text_wrapped(
            draw, body[:100], (self.LEFT_MARGIN + 30, fact_y1 + 60),
            self.font_msmall, "white", self.CONTENT_WIDTH - 60,
            line_spacing=10
        )

        return img

    def generate_slide4_neutral(self, script: Dict) -> Image.Image:
        """Generate Slide 4 (Neutral) - same structure as slide 2/3 but gray theme"""
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        slide_data = script["slides"][3]

        # y=60: label bar + label text (gray)
        bar_color = COLORS["neutral"]
        draw.rectangle((self.LEFT_MARGIN, 60, self.LEFT_MARGIN + 16, 120), fill=self._hex_to_rgb(bar_color))
        draw.text((self.LEFT_MARGIN + 36, 65), "중립·주의", font=self.font_large, fill=self._hex_to_rgb("white"))

        # y=200: sector cards
        sectors = slide_data.get("sectors", [])
        body = slide_data.get("body", "")

        y_offset = 200
        for sector in sectors[:2]:  # Max 2 for neutral
            card_y1 = y_offset
            card_y2 = y_offset + 160

            # Dark gray background
            self._draw_rounded_rect(
                draw,
                (self.LEFT_MARGIN, card_y1, self.WIDTH - self.RIGHT_MARGIN, card_y2),
                radius=20,
                fill="#2A2A2A"  # Dark gray
            )

            # Sector name (gray, 32px bold)
            draw.text((self.LEFT_MARGIN + 30, card_y1 + 30), sector, font=self.font_medium, fill=self._hex_to_rgb(COLORS["neutral"]))

            # Reason text
            reason_y = card_y1 + 80
            self._draw_text_wrapped(
                draw, body[:60], (self.LEFT_MARGIN + 30, reason_y),
                self.font_msmall, "white", self.CONTENT_WIDTH - 60,
                line_spacing=10
            )

            y_offset += 180

        # y=1600: fact box
        fact_y1 = 1600
        fact_y2 = 1800

        self._draw_rounded_rect(
            draw,
            (self.LEFT_MARGIN, fact_y1, self.WIDTH - self.RIGHT_MARGIN, fact_y2),
            radius=20,
            fill="#1A1A1A"
        )

        draw.text((self.LEFT_MARGIN + 30, fact_y1 + 20), "핵심 팩트", font=self.font_xsmall, fill=self._hex_to_rgb("#888888"))

        caution = slide_data.get("caution", body[:100])
        self._draw_text_wrapped(
            draw, caution, (self.LEFT_MARGIN + 30, fact_y1 + 60),
            self.font_msmall, "white", self.CONTENT_WIDTH - 60,
            line_spacing=10
        )

        return img

    def generate_slide5_conclusion(self, script: Dict) -> Image.Image:
        """
        Generate Slide 5 (Conclusion)

        Layout:
        - y=60: "오늘의 결론" (white, 44px bold)
        - y=200: 3 summary rows (colored bar + text, 36px)
        - y=1550: CTA box (green border, rounded)
        - y=1800: disclaimer (gray, 20px, center)
        """
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        slide_data = script["slides"][4]

        # y=60: Title
        draw.text((self.LEFT_MARGIN, 60), "오늘의 결론", font=self.font_xlarge, fill=self._hex_to_rgb("white"))

        # y=200: 3 summary rows
        body_lines = slide_data.get("body", "").split("\n")

        # Green bar row
        y_offset = 200
        draw.rectangle((self.LEFT_MARGIN, y_offset, self.LEFT_MARGIN + 10, y_offset + 50), fill=self._hex_to_rgb(COLORS["bullish"]))
        summary_text = body_lines[0] if len(body_lines) > 0 else "호재 요약"
        draw.text((self.LEFT_MARGIN + 30, y_offset + 10), summary_text[:40], font=self.font_mlarge, fill=self._hex_to_rgb("white"))

        # Red bar row
        y_offset += 100
        draw.rectangle((self.LEFT_MARGIN, y_offset, self.LEFT_MARGIN + 10, y_offset + 50), fill=self._hex_to_rgb(COLORS["bearish"]))
        summary_text = body_lines[1] if len(body_lines) > 1 else "악재 요약"
        draw.text((self.LEFT_MARGIN + 30, y_offset + 10), summary_text[:40], font=self.font_mlarge, fill=self._hex_to_rgb("white"))

        # Gray bar row
        y_offset += 100
        draw.rectangle((self.LEFT_MARGIN, y_offset, self.LEFT_MARGIN + 10, y_offset + 50), fill=self._hex_to_rgb(COLORS["neutral"]))
        summary_text = body_lines[2] if len(body_lines) > 2 else "중립 요약"
        draw.text((self.LEFT_MARGIN + 30, y_offset + 10), summary_text[:40], font=self.font_mlarge, fill=self._hex_to_rgb("white"))

        # y=1550: CTA box
        cta_y1 = 1550
        cta_y2 = 1650

        self._draw_rounded_rect(
            draw,
            (self.LEFT_MARGIN, cta_y1, self.WIDTH - self.RIGHT_MARGIN, cta_y2),
            radius=20,
            fill=None,
            outline=COLORS["brand"],
            width=3
        )

        cta_text = slide_data.get("cta", "자세한 분석은 프로필 링크")
        bbox = draw.textbbox((0, 0), cta_text, font=self.font_medium)
        cta_width = bbox[2] - bbox[0]
        cta_x = (self.WIDTH - cta_width) // 2

        draw.text((cta_x, cta_y1 + 35), cta_text, font=self.font_medium, fill=self._hex_to_rgb(COLORS["brand"]))

        # y=1800: disclaimer
        disclaimer = script.get("disclaimer", "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다")
        bbox = draw.textbbox((0, 0), disclaimer, font=self.font_tiny)
        disclaimer_width = bbox[2] - bbox[0]
        disclaimer_x = (self.WIDTH - disclaimer_width) // 2

        draw.text((disclaimer_x, 1800), disclaimer, font=self.font_tiny, fill=self._hex_to_rgb("#888888"))

        return img

    def generate_all_slides(self, instagram_script: Dict) -> List[Image.Image]:
        """
        Generate all 5 slides

        Args:
            instagram_script: Instagram script dict

        Returns:
            List of 5 PIL Images
        """
        logger.info(f"Generating slides for cluster {instagram_script.get('cluster_id')}...")

        slides = [
            self.generate_slide1_cover(instagram_script),
            self.generate_slide2_bullish(instagram_script),
            self.generate_slide3_bearish(instagram_script),
            self.generate_slide4_neutral(instagram_script),
            self.generate_slide5_conclusion(instagram_script)
        ]

        logger.info(f"Generated {len(slides)} slides")
        return slides

    def save_slides(self, slides: List[Image.Image], cluster_id: str,
                   output_dir: str = "data/6_cards") -> List[str]:
        """
        Save slides as PNG files

        Args:
            slides: List of PIL Images
            cluster_id: Cluster ID
            output_dir: Output directory base path

        Returns:
            List of saved file paths
        """
        cluster_dir = os.path.join(output_dir, f"cluster_{cluster_id}")
        os.makedirs(cluster_dir, exist_ok=True)

        paths = []
        for i, slide in enumerate(slides, 1):
            path = os.path.join(cluster_dir, f"slide_{i}.png")
            slide.save(path, "PNG")
            logger.info(f"Saved: {path}")
            paths.append(path)

        return paths

    def run(self, scripts_path: str = "data/5_generated/scripts.json") -> List[str]:
        """
        Full pipeline: load scripts → generate slides → save → return paths

        Args:
            scripts_path: Input scripts JSON path

        Returns:
            List of all saved file paths
        """
        logger.info("=" * 70)
        logger.info("SignalFeed Card Generator Started")
        logger.info("=" * 70)

        # Load scripts
        with open(scripts_path, 'r', encoding='utf-8') as f:
            scripts_data = json.load(f)

        logger.info(f"Loaded {len(scripts_data)} scripts")

        all_paths = []

        for item in scripts_data:
            try:
                instagram_script = item.get("instagram", {})
                cluster_id = instagram_script.get("cluster_id", "unknown")

                # Generate slides
                slides = self.generate_all_slides(instagram_script)

                # Save
                paths = self.save_slides(slides, cluster_id)
                all_paths.extend(paths)

            except Exception as e:
                logger.error(f"Error generating cards for cluster {item.get('cluster_id')}: {e}")
                continue

        logger.info("=" * 70)
        logger.info(f"Card Generation Complete: {len(all_paths)} cards")
        logger.info("=" * 70)

        return all_paths


if __name__ == "__main__":
    # Test run
    generator = CardGenerator()

    if os.path.exists("data/5_generated/scripts.json"):
        paths = generator.run()
        logger.info(f"Generated {len(paths)} cards")
    else:
        logger.warning("No scripts found. Run content generator first.")
