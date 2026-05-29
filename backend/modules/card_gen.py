"""
SignalFeed Instagram Card Generator
Pillow 기반 1080x1920px 다크모드 카드 이미지 생성
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
    """Instagram 카드 이미지 생성기"""

    # Canvas dimensions (Instagram Story/Reels ratio)
    WIDTH = 1080
    HEIGHT = 1920

    # Padding
    PADDING = 60
    MARGIN = 40

    def __init__(self, font_path: str = "assets/fonts/NanumGothicBold.ttf"):
        """
        Initialize CardGenerator

        Args:
            font_path: Path to Korean font file
        """
        self.font_path = font_path

        # Try to load custom font, fallback to default
        try:
            self.font_large = ImageFont.truetype(font_path, 40)
            self.font_medium = ImageFont.truetype(font_path, 28)
            self.font_small = ImageFont.truetype(font_path, 20)
            self.font_tiny = ImageFont.truetype(font_path, 16)
            logger.info(f"Loaded font: {font_path}")
        except Exception as e:
            logger.warning(f"Failed to load custom font: {e}. Using default font.")
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()

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

    def _draw_rounded_rect(self, draw: ImageDraw.ImageDraw, xy: Tuple[int, int, int, int],
                          radius: int, fill: str, outline: str = None, width: int = 2):
        """
        Draw rounded rectangle

        Args:
            draw: ImageDraw object
            xy: (x1, y1, x2, y2) coordinates
            radius: Corner radius
            fill: Fill color (hex)
            outline: Outline color (hex)
            width: Outline width
        """
        fill_rgb = self._hex_to_rgb(fill)
        outline_rgb = self._hex_to_rgb(outline) if outline else None

        draw.rounded_rectangle(xy, radius=radius, fill=fill_rgb, outline=outline_rgb, width=width)

    def _draw_text_wrapped(self, draw: ImageDraw.ImageDraw, text: str, x: int, y: int,
                          max_width: int, font: ImageFont.FreeTypeFont, color: str,
                          line_spacing: int = 8, align: str = "left") -> int:
        """
        Draw text with word wrapping

        Args:
            draw: ImageDraw object
            text: Text to draw
            x: X coordinate
            y: Y coordinate
            max_width: Maximum width for wrapping
            font: Font object
            color: Text color (hex)
            line_spacing: Space between lines
            align: Text alignment (left/center)

        Returns:
            Final Y coordinate after drawing
        """
        color_rgb = self._hex_to_rgb(color)
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

        current_y = y
        for line in lines:
            if align == "center":
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                line_x = x - line_width // 2
            else:
                line_x = x

            draw.text((line_x, current_y), line, font=font, fill=color_rgb)
            bbox = draw.textbbox((0, 0), line, font=font)
            current_y += (bbox[3] - bbox[1]) + line_spacing

        return current_y

    def generate_slide1_cover(self, script: Dict) -> Image:
        """
        Generate cover slide (Slide 1)

        Args:
            script: Instagram script dict

        Returns:
            PIL Image
        """
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        # Top: SIGNALFEED brand
        draw.text((self.PADDING, self.PADDING), "SIGNALFEED", font=self.font_tiny,
                 fill=self._hex_to_rgb(COLORS["brand"]))

        # Center-top: issue tag
        tag_y = 200
        draw.text((self.PADDING, tag_y), "🔔 오늘의 핵심 이슈", font=self.font_small,
                 fill=self._hex_to_rgb(COLORS["text_secondary"]))

        # Center: issue title
        title = script["slides"][0]["title"]
        title_y = 300
        self._draw_text_wrapped(draw, title, self.WIDTH // 2, title_y,
                               self.WIDTH - 2 * self.PADDING, self.font_large,
                               COLORS["text_primary"], align="center")

        # Center-bottom: signal emoji
        signal = script["signal"]
        emoji = script["slides"][0].get("signal_emoji", "⚪")
        signal_text = f"{emoji} {signal.upper()}"
        signal_y = 600
        draw.text((self.WIDTH // 2, signal_y), signal_text, font=self.font_medium,
                 fill=self._hex_to_rgb(COLORS["text_primary"]), anchor="mm")

        # Bottom: source chips
        source_y = self.HEIGHT - 200
        draw.text((self.WIDTH // 2, source_y), "Reuters · Bloomberg · FT",
                 font=self.font_tiny, fill=self._hex_to_rgb(COLORS["text_tertiary"]),
                 anchor="mm")

        # Bottom: swipe prompt
        swipe_y = self.HEIGHT - 150
        draw.text((self.WIDTH // 2, swipe_y), "슬라이드로 보기 →",
                 font=self.font_small, fill=self._hex_to_rgb(COLORS["brand"]),
                 anchor="mm")

        # Bottom-most: green line accent
        line_y = self.HEIGHT - 80
        draw.rectangle([(self.PADDING, line_y), (self.WIDTH - self.PADDING, line_y + 4)],
                      fill=self._hex_to_rgb(COLORS["brand"]))

        return img

    def generate_slide2_bullish(self, script: Dict) -> Image:
        """
        Generate bullish slide (Slide 2)

        Args:
            script: Instagram script dict

        Returns:
            PIL Image
        """
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        # Top: 호재 label with green bar
        bar_y = self.PADDING
        draw.rectangle([(self.PADDING, bar_y), (self.PADDING + 6, bar_y + 60)],
                      fill=self._hex_to_rgb(COLORS["bullish"]))
        draw.text((self.PADDING + 30, bar_y + 15), "호재", font=self.font_large,
                 fill=self._hex_to_rgb(COLORS["bullish"]))

        # Body: sector cards
        slide_data = script["slides"][1]
        body_text = slide_data.get("body", "")
        sectors = slide_data.get("sectors", [])

        card_y = 200
        card_height = 150

        # Split body by bullet points
        bullets = [line.strip() for line in body_text.split('\n') if line.strip().startswith('•')]

        for i, bullet in enumerate(bullets[:3]):
            # Draw card
            card_rect = (self.PADDING, card_y + i * (card_height + 20),
                        self.WIDTH - self.PADDING, card_y + i * (card_height + 20) + card_height)
            self._draw_rounded_rect(draw, card_rect, 15, COLORS["bullish_bg"],
                                   outline=COLORS["bullish"], width=2)

            # Sector name (if available)
            if i < len(sectors):
                draw.text((self.PADDING + 20, card_y + i * (card_height + 20) + 20),
                         sectors[i], font=self.font_medium, fill=self._hex_to_rgb(COLORS["bullish"]))

            # Reason text
            reason_text = bullet.lstrip('•').strip()
            self._draw_text_wrapped(draw, reason_text,
                                   self.PADDING + 20, card_y + i * (card_height + 20) + 70,
                                   self.WIDTH - 2 * self.PADDING - 40, self.font_small,
                                   COLORS["text_primary"])

        # Bottom: fact box
        fact_y = self.HEIGHT - 300
        fact_rect = (self.PADDING, fact_y, self.WIDTH - self.PADDING, fact_y + 200)
        self._draw_rounded_rect(draw, fact_rect, 15, COLORS["card"])

        draw.text((self.PADDING + 20, fact_y + 20), "📊 핵심 팩트", font=self.font_small,
                 fill=self._hex_to_rgb(COLORS["text_secondary"]))

        fact_text = "금리 인하로 차입 비용 감소, 성장 섹터에 긍정적 영향 예상"
        self._draw_text_wrapped(draw, fact_text, self.PADDING + 20, fact_y + 60,
                               self.WIDTH - 2 * self.PADDING - 40, self.font_small,
                               COLORS["text_primary"])

        return img

    def generate_slide3_bearish(self, script: Dict) -> Image:
        """
        Generate bearish slide (Slide 3)

        Args:
            script: Instagram script dict

        Returns:
            PIL Image
        """
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        # Top: 악재 label with red bar
        bar_y = self.PADDING
        draw.rectangle([(self.PADDING, bar_y), (self.PADDING + 6, bar_y + 60)],
                      fill=self._hex_to_rgb(COLORS["bearish"]))
        draw.text((self.PADDING + 30, bar_y + 15), "악재", font=self.font_large,
                 fill=self._hex_to_rgb(COLORS["bearish"]))

        # Body: sector cards
        slide_data = script["slides"][2]
        body_text = slide_data.get("body", "")
        sectors = slide_data.get("sectors", [])

        card_y = 200
        card_height = 150

        # Split body by bullet points
        bullets = [line.strip() for line in body_text.split('\n') if line.strip().startswith('•')]

        for i, bullet in enumerate(bullets[:3]):
            # Draw card
            card_rect = (self.PADDING, card_y + i * (card_height + 20),
                        self.WIDTH - self.PADDING, card_y + i * (card_height + 20) + card_height)
            self._draw_rounded_rect(draw, card_rect, 15, COLORS["bearish_bg"],
                                   outline=COLORS["bearish"], width=2)

            # Sector name (if available)
            if i < len(sectors):
                draw.text((self.PADDING + 20, card_y + i * (card_height + 20) + 20),
                         sectors[i], font=self.font_medium, fill=self._hex_to_rgb(COLORS["bearish"]))

            # Reason text
            reason_text = bullet.lstrip('•').strip()
            self._draw_text_wrapped(draw, reason_text,
                                   self.PADDING + 20, card_y + i * (card_height + 20) + 70,
                                   self.WIDTH - 2 * self.PADDING - 40, self.font_small,
                                   COLORS["text_primary"])

        # Bottom: fact box
        fact_y = self.HEIGHT - 300
        fact_rect = (self.PADDING, fact_y, self.WIDTH - self.PADDING, fact_y + 200)
        self._draw_rounded_rect(draw, fact_rect, 15, COLORS["card"])

        draw.text((self.PADDING + 20, fact_y + 20), "⚠️ 핵심 팩트", font=self.font_small,
                 fill=self._hex_to_rgb(COLORS["text_secondary"]))

        fact_text = "인플레이션 급등으로 구매력 감소, 소비재 및 소매 섹터 압박"
        self._draw_text_wrapped(draw, fact_text, self.PADDING + 20, fact_y + 60,
                               self.WIDTH - 2 * self.PADDING - 40, self.font_small,
                               COLORS["text_primary"])

        return img

    def generate_slide4_neutral(self, script: Dict) -> Image:
        """
        Generate neutral/caution slide (Slide 4)

        Args:
            script: Instagram script dict

        Returns:
            PIL Image
        """
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        # Top: 중립·주의 label with gray bar
        bar_y = self.PADDING
        draw.rectangle([(self.PADDING, bar_y), (self.PADDING + 6, bar_y + 60)],
                      fill=self._hex_to_rgb(COLORS["neutral"]))
        draw.text((self.PADDING + 30, bar_y + 15), "중립 · 주의", font=self.font_large,
                 fill=self._hex_to_rgb(COLORS["neutral"]))

        # Body: neutral sector cards
        slide_data = script["slides"][3]
        body_text = slide_data.get("body", "")

        card_y = 200
        card_height = 150

        # Split body by bullet points
        bullets = [line.strip() for line in body_text.split('\n') if line.strip().startswith('•')]

        for i, bullet in enumerate(bullets[:3]):
            # Draw card
            card_rect = (self.PADDING, card_y + i * (card_height + 20),
                        self.WIDTH - self.PADDING, card_y + i * (card_height + 20) + card_height)
            self._draw_rounded_rect(draw, card_rect, 15, COLORS["neutral_bg"],
                                   outline=COLORS["neutral"], width=2)

            # Reason text
            reason_text = bullet.lstrip('•').strip()
            self._draw_text_wrapped(draw, reason_text,
                                   self.PADDING + 20, card_y + i * (card_height + 20) + 40,
                                   self.WIDTH - 2 * self.PADDING - 40, self.font_small,
                                   COLORS["text_primary"])

        # Bottom: AI caution box
        caution_y = self.HEIGHT - 350
        caution_rect = (self.PADDING, caution_y, self.WIDTH - self.PADDING, caution_y + 250)
        self._draw_rounded_rect(draw, caution_rect, 15, COLORS["card"])

        draw.text((self.PADDING + 20, caution_y + 20), "🤖 AI 주의 코멘트",
                 font=self.font_small, fill=self._hex_to_rgb(COLORS["text_secondary"]))

        caution_text = slide_data.get("caution", "AI 분석 결과이며, 실제 시장 상황과 다를 수 있습니다.")
        self._draw_text_wrapped(draw, caution_text, self.PADDING + 20, caution_y + 60,
                               self.WIDTH - 2 * self.PADDING - 40, self.font_small,
                               COLORS["text_primary"])

        return img

    def generate_slide5_conclusion(self, script: Dict) -> Image:
        """
        Generate conclusion slide (Slide 5)

        Args:
            script: Instagram script dict

        Returns:
            PIL Image
        """
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self._hex_to_rgb(COLORS["bg"]))
        draw = ImageDraw.Draw(img)

        # Top: 오늘의 결론 label
        draw.text((self.PADDING, self.PADDING), "오늘의 결론", font=self.font_large,
                 fill=self._hex_to_rgb(COLORS["text_primary"]))

        # Body: 3 summary rows
        slide_data = script["slides"][4]
        body_text = slide_data.get("body", "")
        lines = [line.strip() for line in body_text.split('\n') if line.strip()]

        summary_y = 200
        row_height = 100

        colors_list = [COLORS["bullish"], COLORS["bearish"], COLORS["neutral"]]

        for i, line in enumerate(lines[:3]):
            # Color bar
            bar_x = self.PADDING
            bar_rect = (bar_x, summary_y + i * (row_height + 20),
                       bar_x + 6, summary_y + i * (row_height + 20) + row_height)
            draw.rectangle(bar_rect, fill=self._hex_to_rgb(colors_list[i]))

            # Summary text
            self._draw_text_wrapped(draw, line, bar_x + 30,
                                   summary_y + i * (row_height + 20) + 20,
                                   self.WIDTH - bar_x - 50, self.font_medium,
                                   COLORS["text_primary"])

        # CTA box
        cta_y = self.HEIGHT - 400
        cta_rect = (self.PADDING, cta_y, self.WIDTH - self.PADDING, cta_y + 120)
        self._draw_rounded_rect(draw, cta_rect, 15, COLORS["bg"],
                               outline=COLORS["brand"], width=3)

        cta_text = slide_data.get("cta", "자세한 분석 → 프로필 링크")
        draw.text((self.WIDTH // 2, cta_y + 60), cta_text, font=self.font_medium,
                 fill=self._hex_to_rgb(COLORS["brand"]), anchor="mm")

        # Bottom: disclaimer
        disclaimer_y = self.HEIGHT - 200
        disclaimer = script.get("disclaimer", "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다")
        self._draw_text_wrapped(draw, disclaimer, self.WIDTH // 2, disclaimer_y,
                               self.WIDTH - 2 * self.PADDING, self.font_tiny,
                               COLORS["text_tertiary"], align="center")

        return img

    def generate_all_slides(self, script: Dict) -> List[Image.Image]:
        """
        Generate all 5 slides

        Args:
            script: Instagram script dict

        Returns:
            List of PIL Images
        """
        logger.info(f"Generating slides for cluster {script.get('cluster_id')}...")

        slides = [
            self.generate_slide1_cover(script),
            self.generate_slide2_bullish(script),
            self.generate_slide3_bearish(script),
            self.generate_slide4_neutral(script),
            self.generate_slide5_conclusion(script)
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
            output_dir: Output directory

        Returns:
            List of saved file paths
        """
        cluster_dir = os.path.join(output_dir, f"cluster_{cluster_id}")
        os.makedirs(cluster_dir, exist_ok=True)

        paths = []

        for i, slide in enumerate(slides, start=1):
            path = os.path.join(cluster_dir, f"slide_{i}.png")
            slide.save(path, "PNG")
            paths.append(path)
            logger.info(f"Saved: {path}")

        return paths

    def run(self, scripts_path: str = "data/5_generated/scripts.json") -> Dict:
        """
        Full pipeline: load scripts → generate slides → save → return paths

        Args:
            scripts_path: Input scripts JSON path

        Returns:
            Dict mapping cluster_id to list of slide paths
        """
        logger.info("=" * 70)
        logger.info("SignalFeed Card Generator Started")
        logger.info("=" * 70)

        # Load scripts
        logger.info(f"Loading scripts from {scripts_path}...")
        with open(scripts_path, 'r', encoding='utf-8') as f:
            scripts_data = json.load(f)

        logger.info(f"Loaded {len(scripts_data)} scripts")

        # Generate and save slides for each cluster
        all_paths = {}

        for item in scripts_data:
            cluster_id = str(item.get("cluster_id", -1))
            instagram_script = item.get("instagram", {})

            # Generate slides
            slides = self.generate_all_slides(instagram_script)

            # Save slides
            paths = self.save_slides(slides, cluster_id)

            all_paths[cluster_id] = paths

        logger.info("=" * 70)
        logger.info(f"Card Generation Complete: {len(all_paths)} clusters")
        logger.info("=" * 70)

        return all_paths


if __name__ == "__main__":
    # Test run
    generator = CardGenerator()

    # Use sample data if exists
    sample_path = "data/5_generated/scripts.json"
    if os.path.exists(sample_path):
        paths = generator.run(sample_path)
        logger.info(f"Generated cards for {len(paths)} clusters")
    else:
        logger.warning(f"Sample data not found at {sample_path}")
