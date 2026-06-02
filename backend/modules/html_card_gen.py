"""
SignalFeed HTML Card Generator
B-Style Newsfeed Design: 다크 커버 + 화이트 내지
"""

import os
import json
import logging
import re
from typing import List, Dict
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HTMLCardGenerator:
    """HTML + Playwright 기반 Instagram 카드 생성기 (B-Style Newsfeed)"""

    # Canvas dimensions (Instagram 4:5 ratio)
    WIDTH = 1080
    HEIGHT = 1350

    # Design System - B Style
    COLORS = {
        # Cover (dark)
        "cover_bg": "#111111",
        "cover_text": "#FFFFFF",
        "cover_secondary": "#AAAAAA",

        # Inner pages (white base)
        "white": "#FFFFFF",
        "black": "#111111",
        "gray_light": "#F0F0F0",
        "gray_mid": "#AAAAAA",
        "gray_dark": "#444444",

        # Signal colors
        "bullish": "#00C853",
        "bullish_dark": "#0F6E56",
        "bullish_light": "#E8FAF0",
        "bullish_border": "#C0E8C0",
        "bullish_card_bg": "#F0FFF4",

        "bearish": "#FF3D3D",
        "bearish_dark": "#993C1D",
        "bearish_light": "#FEF0E8",
        "bearish_border": "#F5C4B3",
        "bearish_card_bg": "#FFF5F5",

        "neutral": "#888888",

        # UI elements
        "brand": "#00C853",
        "divider": "#F0F0F0",
        "bg_subtle": "#F8F8F6",
    }

    def __init__(self):
        """Initialize HTMLCardGenerator"""
        pass

    def _get_font_css(self) -> str:
        """Get Google Fonts CSS"""
        return """
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700;900&family=Noto+Sans+KR:wght@400;500;700&display=swap');
    """

    def _get_base_styles(self) -> str:
        """Get base CSS styles"""
        return """
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeLegibility;
    }

    .serif {
      font-family: 'Noto Serif KR', serif;
    }

    .sans {
      font-family: 'Noto Sans KR', sans-serif;
    }

    .card {
      width: 1080px;
      height: 1350px;
      position: relative;
      overflow: hidden;
    }
    """

    def _extract_numbers_from_text(self, text: str) -> List[str]:
        """Extract numbers with units from text for badge display"""
        # Match patterns like: 3.2%, $50억, 0.25%p, +2.1%, -1.5%
        pattern = r'[+-]?\d+\.?\d*\s*[%$억달러만원↑↓]|[+-]?\d+\.?\d*%p|[+-]?\d+\.?\d*bp'
        matches = re.findall(pattern, text)
        return matches[:3]  # Max 3 badges

    def _highlight_numbers(self, text: str, color: str = None) -> str:
        """Highlight numbers in text with color"""
        if color is None:
            color = self.COLORS["bullish"]
        pattern = r'(\d+\.?\d*\s*[%$억달러만원↑↓]|[+-]?\d+\.?\d*%p|[+-]?\d+\.?\d*bp)'
        def replacer(match):
            num = match.group(1)
            return f'<span style="color:{color};font-weight:700;">{num}</span>'
        return re.sub(pattern, replacer, text)

    def _generate_slide1_html(self, slide_data: Dict, pexels_image_path: str, slide_num: int) -> str:
        """Slide 1: Cover — 다크 배경 + Pexels 이미지 + 수치 배지"""
        hook_title = slide_data.get("hook_title", "")
        one_line = slide_data.get("one_line", "")
        sources = slide_data.get("sources", [])
        source_text = " · ".join(sources) if sources else "Reuters · Bloomberg · FT"

        # Extract numbers for badges
        numbers = self._extract_numbers_from_text(one_line)

        # Generate badge HTML
        badges_html = ""
        for num in numbers:
            # Determine badge style based on sign
            if num.startswith('+') or '↑' in num or '%' in num and not num.startswith('-'):
                bg_color = self.COLORS["bullish_light"]
                text_color = self.COLORS["bullish_dark"]
                border_color = self.COLORS["bullish_border"]
            elif num.startswith('-') or '↓' in num:
                bg_color = self.COLORS["bearish_light"]
                text_color = self.COLORS["bearish_dark"]
                border_color = self.COLORS["bearish_border"]
            else:
                bg_color = self.COLORS["bullish_light"]
                text_color = self.COLORS["bullish_dark"]
                border_color = self.COLORS["bullish_border"]

            badges_html += f"""
    <div style="background: {bg_color}; color: {text_color}; border: 1px solid {border_color}; font-size: 22px; font-weight: 700; padding: 8px 20px; border-radius: 8px;">
      {num}
    </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS['cover_bg']};">
  <!-- Pexels background image: y=0~600px -->
  <div style="position: absolute; top: 0; left: 0; width: 1080px; height: 600px; overflow: hidden;">
    <img src="{pexels_image_path}" style="width: 100%; height: 100%; object-fit: cover;">
    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to bottom, transparent 30%, {self.COLORS['cover_bg']} 100%);"></div>
  </div>

  <!-- SIGNALFEED brand: top-left -->
  <div style="position: absolute; top: 28px; left: 40px; font-size: 13px; letter-spacing: 0.15em; font-weight: 700; color: {self.COLORS['brand']}; text-transform: uppercase;">
    SIGNALFEED
  </div>

  <!-- Hook title: y=620px -->
  <h1 class="serif" style="position: absolute; top: 620px; left: 40px; right: 40px; font-size: 84px; font-weight: 900; color: {self.COLORS['cover_text']}; line-height: 1.15; letter-spacing: -0.03em;">
    {hook_title}
  </h1>

  <!-- One-line summary: y=870px -->
  <p class="sans" style="position: absolute; top: 870px; left: 40px; right: 40px; font-size: 22px; color: {self.COLORS['cover_secondary']}; line-height: 1.5;">
    {one_line}
  </p>

  <!-- Number badges: y=950px -->
  <div style="position: absolute; top: 950px; left: 40px; display: flex; flex-direction: row; gap: 12px; flex-wrap: wrap;">
    {badges_html}
  </div>

  <!-- Source: y=1280px -->
  <p class="sans" style="position: absolute; top: 1280px; left: 40px; font-size: 16px; color: #555555;">
    출처: {source_text}
  </p>

  <!-- Bottom green line: y=1347px -->
  <div style="position: absolute; top: 1347px; left: 0; width: 1080px; height: 3px; background: {self.COLORS['brand']};"></div>
</div>
"""

    def _generate_slide2_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 2: Context — 화이트 배경 + 팩트 3개 + 수치 강조"""
        title = slide_data.get("title", "무슨 일이?")
        facts = slide_data.get("facts", [])
        source = slide_data.get("source", "")

        # Generate facts HTML (3 blocks, each 380px)
        facts_html = ""
        for i, fact in enumerate(facts[:3]):
            y_start = 100 + (i * 380)
            fact_num = f"{i+1:02d}"
            highlighted_fact = self._highlight_numbers(fact, self.COLORS["bullish"])

            # Divider between blocks
            divider = f'<div style="position: absolute; top: {y_start}px; left: 0; width: 1080px; height: 1px; background: {self.COLORS["divider"]};"></div>' if i > 0 else ""

            facts_html += f"""
  {divider}
  <!-- Fact block {i+1}: y={y_start}~{y_start+380}px -->
  <div style="position: absolute; top: {y_start}px; left: 0; right: 0; height: 380px; background: {self.COLORS['white']}; border-left: 4px solid {self.COLORS['bullish']}; padding: 40px;">
    <!-- Watermark number -->
    <div class="serif" style="position: absolute; top: 20px; right: 40px; font-size: 120px; font-weight: 900; color: {self.COLORS['gray_light']}; z-index: 0;">
      {fact_num}
    </div>
    <!-- Fact text -->
    <p class="sans" style="position: relative; z-index: 1; font-size: 30px; font-weight: 500; color: {self.COLORS['black']}; line-height: 1.6;">
      {highlighted_fact}
    </p>
  </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS['white']};">
  <!-- Header bar: background black -->
  <div style="position: absolute; top: 0; left: 0; right: 0; height: 100px; background: {self.COLORS['black']}; display: flex; align-items: center; justify-content: space-between; padding: 0 40px;">
    <span class="sans" style="font-size: 13px; letter-spacing: 0.15em; font-weight: 700; color: {self.COLORS['brand']}; text-transform: uppercase;">SIGNALFEED</span>
    <h2 class="serif" style="font-size: 36px; font-weight: 700; color: {self.COLORS['white']};">
      {title}
    </h2>
    <span class="sans" style="font-size: 14px; color: #555555;">
      {slide_num}/5
    </span>
  </div>

  <!-- Fact blocks -->
  {facts_html}

  <!-- Source: y=1290px -->
  <p class="sans" style="position: absolute; top: 1290px; left: 40px; font-size: 16px; color: {self.COLORS['gray_mid']};">
    출처: {source}
  </p>
</div>
"""

    def _generate_slide3_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 3: Bullish — 화이트 배경 + 녹색 카드"""
        title = slide_data.get("title", "↑ 수혜주는?")
        sectors = slide_data.get("sectors", [])
        fact = slide_data.get("fact", "")

        # Determine card height based on count
        num_sectors = len(sectors)
        if num_sectors == 2:
            card_height = 500
            gap = 8
        else:  # 3 sectors
            card_height = 330
            gap = 8

        # Generate sector cards
        sectors_html = ""
        for i, sector in enumerate(sectors):
            y_start = 108 + (i * (card_height + gap))
            name = sector.get("name", "")
            reason = sector.get("reason", "")

            sectors_html += f"""
  <!-- Sector card {i+1}: y={y_start}~{y_start+card_height}px -->
  <div style="position: absolute; top: {y_start}px; left: 40px; right: 40px; height: {card_height}px; background: {self.COLORS['bullish_card_bg']}; border: 1px solid {self.COLORS['bullish_border']}; border-radius: 12px; padding: 40px; display: flex; flex-direction: column; justify-content: center;">
    <h3 class="serif" style="font-size: 72px; font-weight: 900; color: {self.COLORS['bullish_dark']}; letter-spacing: -0.02em;">
      {name}
    </h3>
    <p class="sans" style="margin-top: 12px; font-size: 26px; color: {self.COLORS['gray_dark']}; line-height: 1.5;">
      {reason}
    </p>
  </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS['white']};">
  <!-- Header bar -->
  <div style="position: absolute; top: 0; left: 0; right: 0; height: 100px; background: {self.COLORS['black']}; display: flex; align-items: center; justify-content: space-between; padding: 0 40px;">
    <span class="sans" style="font-size: 13px; letter-spacing: 0.15em; font-weight: 700; color: {self.COLORS['brand']}; text-transform: uppercase;">SIGNALFEED</span>
    <h2 class="serif" style="font-size: 36px; font-weight: 700; color: {self.COLORS['bullish']};">
      {title}
    </h2>
    <span class="sans" style="font-size: 14px; color: #555555;">
      {slide_num}/5
    </span>
  </div>

  <!-- Sector cards -->
  {sectors_html}

  <!-- FACT box: y=1130px~1350px -->
  <div style="position: absolute; top: 1130px; left: 0; right: 0; height: 220px; background: {self.COLORS['bg_subtle']}; border-top: 2px solid {self.COLORS['bullish']}; padding: 32px 40px;">
    <p class="sans" style="font-size: 14px; letter-spacing: 0.12em; color: {self.COLORS['bullish']}; font-weight: 700; margin-bottom: 12px;">
      FACT /
    </p>
    <p class="sans" style="font-size: 22px; color: #555555; line-height: 1.6;">
      {fact}
    </p>
  </div>
</div>
"""

    def _generate_slide4_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 4: Bearish — 화이트 배경 + 빨간색 카드"""
        title = slide_data.get("title", "↓ 주의할 섹터는?")
        sectors = slide_data.get("sectors", [])
        fact = slide_data.get("fact", "")

        # Determine card height based on count
        num_sectors = len(sectors)
        if num_sectors == 2:
            card_height = 500
            gap = 8
        else:  # 3 sectors
            card_height = 330
            gap = 8

        # Generate sector cards
        sectors_html = ""
        for i, sector in enumerate(sectors):
            y_start = 108 + (i * (card_height + gap))
            name = sector.get("name", "")
            reason = sector.get("reason", "")

            sectors_html += f"""
  <!-- Sector card {i+1}: y={y_start}~{y_start+card_height}px -->
  <div style="position: absolute; top: {y_start}px; left: 40px; right: 40px; height: {card_height}px; background: {self.COLORS['bearish_card_bg']}; border: 1px solid {self.COLORS['bearish_border']}; border-radius: 12px; padding: 40px; display: flex; flex-direction: column; justify-content: center;">
    <h3 class="serif" style="font-size: 72px; font-weight: 900; color: {self.COLORS['bearish_dark']}; letter-spacing: -0.02em;">
      {name}
    </h3>
    <p class="sans" style="margin-top: 12px; font-size: 26px; color: {self.COLORS['gray_dark']}; line-height: 1.5;">
      {reason}
    </p>
  </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS['white']};">
  <!-- Header bar -->
  <div style="position: absolute; top: 0; left: 0; right: 0; height: 100px; background: {self.COLORS['black']}; display: flex; align-items: center; justify-content: space-between; padding: 0 40px;">
    <span class="sans" style="font-size: 13px; letter-spacing: 0.15em; font-weight: 700; color: {self.COLORS['brand']}; text-transform: uppercase;">SIGNALFEED</span>
    <h2 class="serif" style="font-size: 36px; font-weight: 700; color: {self.COLORS['bearish']};">
      {title}
    </h2>
    <span class="sans" style="font-size: 14px; color: #555555;">
      {slide_num}/5
    </span>
  </div>

  <!-- Sector cards -->
  {sectors_html}

  <!-- FACT box: y=1130px~1350px -->
  <div style="position: absolute; top: 1130px; left: 0; right: 0; height: 220px; background: {self.COLORS['bg_subtle']}; border-top: 2px solid {self.COLORS['bearish']}; padding: 32px 40px;">
    <p class="sans" style="font-size: 14px; letter-spacing: 0.12em; color: {self.COLORS['bearish']}; font-weight: 700; margin-bottom: 12px;">
      FACT /
    </p>
    <p class="sans" style="font-size: 22px; color: #555555; line-height: 1.6;">
      {fact}
    </p>
  </div>
</div>
"""

    def _generate_slide5_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 5: Conclusion — 화이트 배경 + 요약 + CTA"""
        title = slide_data.get("title", "오늘의 핵심")
        summaries = slide_data.get("summaries", [])
        watch_point = slide_data.get("watch_point", "")
        disclaimer = slide_data.get("disclaimer", "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다")

        # Generate summary blocks (3 blocks, each 200px)
        summaries_html = ""
        colors = [self.COLORS["bullish"], self.COLORS["bearish"], self.COLORS["neutral"]]
        for i, summary in enumerate(summaries[:3]):
            y_start = 108 + (i * 200)
            border_color = colors[i]

            # Divider between blocks
            divider = f'<div style="position: absolute; top: {y_start}px; left: 0; width: 1080px; height: 1px; background: {self.COLORS["divider"]};"></div>' if i > 0 else ""

            summaries_html += f"""
  {divider}
  <!-- Summary block {i+1}: y={y_start}~{y_start+200}px -->
  <div style="position: absolute; top: {y_start}px; left: 0; right: 0; height: 200px; background: {self.COLORS['white']}; border-left: 8px solid {border_color}; padding: 40px; display: flex; align-items: center;">
    <p class="sans" style="font-size: 30px; font-weight: 700; color: {self.COLORS['black']}; line-height: 1.5;">
      {summary}
    </p>
  </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS['white']};">
  <!-- Header bar -->
  <div style="position: absolute; top: 0; left: 0; right: 0; height: 100px; background: {self.COLORS['black']}; display: flex; align-items: center; padding: 0 40px;">
    <h2 class="serif" style="font-size: 36px; font-weight: 900; color: {self.COLORS['white']};">
      {title}
    </h2>
  </div>

  <!-- Summary blocks -->
  {summaries_html}

  <!-- Watch point box: y=720px -->
  <div style="position: absolute; top: 720px; left: 40px; right: 40px; background: {self.COLORS['bg_subtle']}; border-left: 4px solid {self.COLORS['bullish']}; padding: 32px 40px; border-radius: 8px;">
    <p class="sans" style="font-size: 14px; letter-spacing: 0.1em; color: {self.COLORS['bullish']}; font-weight: 700; margin-bottom: 12px;">
      주목 포인트
    </p>
    <p class="sans" style="font-size: 24px; color: {self.COLORS['gray_dark']}; line-height: 1.6;">
      {watch_point}
    </p>
  </div>

  <!-- CTA box: y=1020px -->
  <div style="position: absolute; top: 1020px; left: 40px; right: 40px; background: {self.COLORS['black']}; border-radius: 12px; padding: 40px; text-align: center;">
    <p class="sans" style="font-size: 30px; font-weight: 700; color: {self.COLORS['white']}; margin-bottom: 12px;">
      댓글에 '분석' 남겨주세요
    </p>
    <p class="sans" style="font-size: 22px; color: {self.COLORS['brand']};">
      → 상세 리포트 DM으로 드립니다
    </p>
  </div>

  <!-- Disclaimer: y=1300px -->
  <p class="sans" style="position: absolute; top: 1300px; left: 0; right: 0; text-align: center; font-size: 14px; color: {self.COLORS['gray_mid']};">
    {disclaimer}
  </p>
</div>
"""

    def generate_all_slides(self, script: Dict, pexels_image_path: str = None) -> str:
        """Generate HTML for all 5 slides"""
        # Access instagram object if present
        instagram = script.get("instagram", script)
        cluster_id = instagram.get("cluster_id", script.get("cluster_id", 0))
        slides = instagram.get("slides", [])

        if not pexels_image_path:
            pexels_image_path = f"data/temp/pexels_{cluster_id}.jpg"

        # Convert to absolute file:// path for Playwright
        pexels_image_path = f"file://{os.path.abspath(pexels_image_path)}"

        html_parts = []

        for i, slide in enumerate(slides):
            slide_num = i + 1
            slide_type = slide.get("type", "")

            if slide_type == "cover":
                html = self._generate_slide1_html(slide, pexels_image_path, slide_num)
            elif slide_type == "context":
                html = self._generate_slide2_html(slide, slide_num)
            elif slide_type in ("bullish", "beneficiary"):
                html = self._generate_slide3_html(slide, slide_num)
            elif slide_type in ("bearish", "victim"):
                html = self._generate_slide4_html(slide, slide_num)
            elif slide_type == "conclusion":
                html = self._generate_slide5_html(slide, slide_num)
            else:
                logger.warning(f"Unknown slide type: {slide_type}")
                continue

            html_parts.append(html)

        # Combine all slides
        font_css = self._get_font_css()
        base_styles = self._get_base_styles()

        full_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SignalFeed Card - Cluster {cluster_id}</title>
  <style>
    {font_css}
    {base_styles}
  </style>
</head>
<body>
  {''.join(html_parts)}
</body>
</html>
"""
        return full_html

    def save_html(self, html: str, output_path: str):
        """Save HTML to file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML saved: {output_path}")

    def screenshot_slides(self, html_path: str, output_dir: str, num_slides: int = 5) -> List[str]:
        """Take screenshots of all slides using Playwright"""
        import subprocess

        os.makedirs(output_dir, exist_ok=True)
        output_paths = []

        # Convert to absolute file:// URL
        html_url = f"file://{os.path.abspath(html_path)}"

        for slide_num in range(1, num_slides + 1):
            output_path = os.path.join(output_dir, f"slide_{slide_num}.png")
            selector = f"#slide-{slide_num}"

            try:
                # Use Playwright CLI for screenshot
                cmd = [
                    "python", "-m", "playwright._impl._driver", "screenshot",
                    html_url,
                    output_path,
                    "--selector", selector,
                    "--timeout", "30000",
                    "--viewport-size", f"{self.WIDTH},{self.HEIGHT}",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    logger.info(f"Slide {slide_num} saved: {output_path}")
                    output_paths.append(output_path)
                else:
                    logger.error(f"Screenshot failed for slide {slide_num}: {result.stderr}")
                    # Fallback to Python API
                    self._screenshot_with_python_api(html_url, selector, output_path)
                    output_paths.append(output_path)

            except Exception as e:
                logger.error(f"Error screenshotting slide {slide_num}: {e}")
                # Fallback to Python API
                try:
                    self._screenshot_with_python_api(html_url, selector, output_path)
                    output_paths.append(output_path)
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")

        return output_paths

    def _screenshot_with_python_api(self, url: str, selector: str, output_path: str):
        """Fallback: Use Python Playwright API"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": self.WIDTH, "height": self.HEIGHT})
            page.goto(url)
            page.wait_for_load_state("networkidle")

            # Wait for fonts
            page.evaluate("document.fonts.ready")

            element = page.query_selector(selector)
            if element:
                element.screenshot(path=output_path)
                logger.info(f"Screenshot saved (Python API): {output_path}")
            else:
                logger.error(f"Selector not found: {selector}")

            browser.close()

    def run(self, input_path: str = "data/3_generated/scripts.json") -> int:
        """Main pipeline: Generate cards for all clusters"""
        logger.info("=" * 70)
        logger.info("SignalFeed Card Generation Started (B-Style Newsfeed)")
        logger.info("=" * 70)

        # Load scripts
        with open(input_path, "r", encoding="utf-8") as f:
            scripts = json.load(f)

        logger.info(f"Loaded {len(scripts)} scripts")

        # Process each cluster
        from .image_fetcher import ImageFetcher
        image_fetcher = ImageFetcher()

        total_generated = 0

        for script in scripts:
            # Access instagram object
            instagram = script.get("instagram", script)
            cluster_id = instagram.get("cluster_id", script.get("cluster_id", 0))
            pexels_keyword = instagram.get("pexels_keyword", "global economy finance business")

            # Fetch Pexels image
            logger.info(f"Fetching Pexels image: {pexels_keyword}")
            pexels_image = image_fetcher.fetch_with_fallback([pexels_keyword])

            # Save Pexels image temporarily
            temp_dir = "data/temp"
            os.makedirs(temp_dir, exist_ok=True)
            pexels_path = os.path.join(temp_dir, f"pexels_{cluster_id}.jpg")
            pexels_image.save(pexels_path, "JPEG", quality=95)
            logger.info(f"Saved Pexels image: {pexels_path}")

            # Generate HTML (pass instagram object)
            html = self.generate_all_slides(instagram, pexels_path)
            html_path = os.path.join(temp_dir, f"card_{cluster_id}.html")
            self.save_html(html, html_path)

            # Take screenshots
            output_dir = f"data/4_cards/cluster_{cluster_id}"
            slide_paths = self.screenshot_slides(html_path, output_dir, num_slides=5)

            if len(slide_paths) == 5:
                logger.info(f"All 5 slides saved to {output_dir}")
                total_generated += 1
            else:
                logger.warning(f"Only {len(slide_paths)}/5 slides generated for cluster {cluster_id}")

            logger.info(f"Cluster {cluster_id}: {len(slide_paths)} cards generated")

        logger.info("=" * 70)
        logger.info(f"Card Generation Complete: {total_generated} clusters")
        logger.info("=" * 70)

        return total_generated


if __name__ == "__main__":
    generator = HTMLCardGenerator()
    generator.run()
