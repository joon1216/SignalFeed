"""
SignalFeed HTML Card Generator
AIMing 스타일 참고: 텍스트 크고 굵게, 공백 없이 꽉 채움, 수치 강조
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
    """HTML + Playwright 기반 Instagram 카드 생성기 (AIMing 스타일)"""

    # Canvas dimensions (Instagram 4:5 ratio)
    WIDTH = 1080
    HEIGHT = 1350

    # New Design System (AIMing-inspired)
    COLORS = {
        "bg": "#0D0D0D",
        "surface": "#161616",
        "card_bg": "#111111",
        "bullish": "#00C853",
        "bearish": "#FF3D3D",
        "neutral": "#888888",
        "text_primary": "#FFFFFF",
        "text_secondary": "#AAAAAA",
        "divider": "#222222",
        "brand": "#00C853",
    }

    def __init__(self):
        """Initialize HTMLCardGenerator"""
        pass

    def _get_font_css(self) -> str:
        """Get Google Fonts CSS"""
        return """
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700;900&family=Noto+Sans+KR:wght@400;700&display=swap');
    """

    def _highlight_numbers(self, text: str, color: str = None) -> str:
        """
        숫자+단위 하이라이팅

        Args:
            text: 원본 텍스트
            color: 하이라이트 색상 (None이면 bullish 사용)

        Returns:
            하이라이트된 HTML 텍스트
        """
        if color is None:
            color = self.COLORS["bullish"]

        # 정규식: 숫자 + 단위 (%, $, 억, 달러, 만, 원, ↑, ↓, %p, bp)
        pattern = r'(\d+\.?\d*\s*[%$억달러만원↑↓]|[+-]?\d+\.?\d*%p|[+-]?\d+\.?\d*bp)'

        def replacer(match):
            num = match.group(1)
            return f'<span style="color:{color};font-weight:700;">{num}</span>'

        return re.sub(pattern, replacer, text)

    def generate_html(self, script: Dict, image_path: str) -> str:
        """
        Generate complete HTML with all 5 slides

        Args:
            script: Instagram script from content_gen.py
            image_path: Local path to Pexels cover image

        Returns:
            Complete HTML string
        """
        slides_data = script.get("slides", [])
        cluster_id = script.get("cluster_id", "unknown")

        # Generate each slide HTML
        slide_htmls = []

        for i, slide_data in enumerate(slides_data, start=1):
            slide_type = slide_data.get("type")

            if slide_type == "cover":
                slide_htmls.append(self._generate_slide1_html(slide_data, image_path, i))
            elif slide_type == "context":
                slide_htmls.append(self._generate_slide2_html(slide_data, i))
            elif slide_type in ("bullish", "beneficiary"):
                slide_htmls.append(self._generate_slide3_html(slide_data, i))
            elif slide_type in ("bearish", "victim"):
                slide_htmls.append(self._generate_slide4_html(slide_data, i))
            elif slide_type == "conclusion":
                slide_htmls.append(self._generate_slide5_html(slide_data, i))

        # Combine into full HTML document
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SignalFeed Cards - Cluster {cluster_id}</title>
  <style>
    {self._get_font_css()}
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      font-family: 'Noto Sans KR', -apple-system, sans-serif;
      background: #000;
      color: {self.COLORS["text_primary"]};
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }}

    .card {{
      width: {self.WIDTH}px;
      height: {self.HEIGHT}px;
      position: relative;
      overflow: hidden;
      margin-bottom: 20px;
    }}

    /* Typography */
    .serif {{
      font-family: 'Noto Serif KR', serif;
    }}

    .sans {{
      font-family: 'Noto Sans KR', sans-serif;
    }}

    /* Micro brand */
    .micro-brand {{
      position: absolute;
      top: 30px;
      left: 30px;
      font-size: 13px;
      letter-spacing: 0.2em;
      font-weight: 700;
      color: {self.COLORS["brand"]};
      text-transform: uppercase;
      z-index: 10;
    }}
  </style>
</head>
<body>

{''.join(slide_htmls)}

</body>
</html>"""

        return html

    def _generate_slide1_html(self, slide_data: Dict, image_path: str, slide_num: int) -> str:
        """Slide 1: Cover — AIMing 스타일 (상단 50% 이미지, 하단 50% 단색)"""
        hook_title = slide_data.get("hook_title", "")
        one_line = slide_data.get("one_line", "")
        sources = slide_data.get("sources", ["Reuters", "Bloomberg"])

        sources_text = " · ".join(sources[:3])

        # Use absolute file:// URL for image
        img_url = f"file://{os.path.abspath(image_path)}"

        # Date placeholder (현재 날짜)
        from datetime import datetime
        date_str = datetime.now().strftime("%Y.%m.%d")

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS["bg"]};">
  <!-- Top 50%: Image -->
  <div style="position: absolute; top: 0; left: 0; right: 0; height: 675px; background-image: url('{img_url}'); background-size: cover; background-position: center;"></div>

  <!-- Bottom 50%: Dark solid -->
  <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 675px; background: {self.COLORS["bg"]}; padding: 40px;">
    <!-- Date line -->
    <p style="font-size: 18px; color: #666666; margin-bottom: 20px;">
      {date_str} · 글로벌 경제
    </p>

    <!-- Hook title (HUGE) -->
    <h1 class="serif" style="font-size: 80px; font-weight: 900; line-height: 1.2; letter-spacing: -0.02em; color: {self.COLORS["text_primary"]}; margin-bottom: 24px;">
      {hook_title.replace(chr(10), '<br>')}
    </h1>

    <!-- One-line -->
    <p class="sans" style="font-size: 24px; line-height: 1.4; color: #AAAAAA; margin-bottom: 32px;">
      {one_line}
    </p>

    <!-- Bottom: Sources + Signal badge -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto;">
      <p style="font-size: 18px; color: #666666;">
        {sources_text}
      </p>
      <div style="background: {self.COLORS["bullish"]}; padding: 8px 24px; border-radius: 20px;">
        <span class="sans" style="font-size: 14px; font-weight: 700; color: #000; letter-spacing: 0.05em;">
          시그널
        </span>
      </div>
    </div>
  </div>

  <!-- Top-left brand -->
  <div class="micro-brand">SIGNALFEED</div>
</div>
"""

    def _generate_slide2_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 2: Context — 꽉 채우기, 수치 강조"""
        title = slide_data.get("title", "무슨 일이?")
        facts = slide_data.get("facts", [])
        source = slide_data.get("source", "")

        # Total content area: y=120 → y=1300 (1180px)
        # 3 fact blocks, equal height
        num_facts = len(facts)
        block_height = 1180 // num_facts if num_facts > 0 else 390

        facts_html = ""
        for i, fact in enumerate(facts):
            y_pos = 120 + (i * block_height)

            # Highlight numbers in green
            highlighted_fact = self._highlight_numbers(fact, self.COLORS["bullish"])

            # Fact number watermark
            fact_num = f"{i+1:02d}"

            facts_html += f"""
    <div style="position: absolute; top: {y_pos}px; left: 0; right: 0; height: {block_height}px; background: {self.COLORS["surface"]}; border-left: 4px solid {self.COLORS["bullish"]}; padding: 28px 40px; display: flex; align-items: center;">
      <div style="position: absolute; top: 12px; right: 40px; font-size: 100px; font-weight: 900; color: #1A1A1A; z-index: 0;">
        {fact_num}
      </div>
      <p class="sans" style="font-size: 28px; line-height: 1.6; letter-spacing: -0.01em; color: {self.COLORS["text_primary"]}; position: relative; z-index: 1;">
        {highlighted_fact}
      </p>
    </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS["bg"]};">
  <div class="micro-brand">SIGNALFEED</div>

  <!-- Title -->
  <div style="position: absolute; top: 40px; left: 40px;">
    <h2 class="serif" style="font-size: 52px; font-weight: 700; color: {self.COLORS["text_primary"]};">
      {title}
    </h2>
  </div>

  <!-- Fact blocks (stacked, no gaps) -->
  {facts_html}

  <!-- Source badge -->
  <p style="position: absolute; bottom: 30px; left: 40px; font-size: 14px; color: #444444;">
    출처: {source}
  </p>
</div>
"""

    def _generate_slide3_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 3: Bullish — 섹터 카드, 공간 분할"""
        return self._generate_sector_slide_html(slide_data, slide_num, "↑ 수혜주는?", self.COLORS["bullish"], is_bearish=False)

    def _generate_slide4_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 4: Bearish — 섹터 카드, 공간 분할"""
        return self._generate_sector_slide_html(slide_data, slide_num, "↓ 주의할 섹터는?", self.COLORS["bearish"], is_bearish=True)

    def _generate_sector_slide_html(self, slide_data: Dict, slide_num: int, label: str, color: str, is_bearish: bool = False) -> str:
        """Generate sector slide — 카드 형태로 공간 분할"""
        sectors = slide_data.get("sectors", [])
        fact = slide_data.get("fact", "")

        # Content area: y=200 → y=1150 (950px for sectors)
        num_sectors = len(sectors)
        total_gap = (num_sectors - 1) * 12  # 12px gap between cards
        card_height = (950 - total_gap) // num_sectors if num_sectors > 0 else 300

        # Card background color (very dark tinted)
        card_bg = "#0F1F0F" if not is_bearish else "#1F0F0F"
        border_color = f"{color}33"  # 20% opacity

        sectors_html = ""
        for i, sector in enumerate(sectors):
            name = sector.get("name", "")
            reason = sector.get("reason", "")
            example_stocks = sector.get("example_stocks", "")

            y_pos = 200 + (i * (card_height + 12))

            # Highlight numbers in sector reason
            highlight_color = self.COLORS["bearish"] if is_bearish else self.COLORS["bullish"]
            highlighted_reason = self._highlight_numbers(reason, highlight_color)

            sectors_html += f"""
    <div style="position: absolute; top: {y_pos}px; left: 40px; right: 40px; height: {card_height}px; background: {card_bg}; border: 1px solid {border_color}; padding: 32px; display: flex; flex-direction: column; justify-content: center; border-radius: 8px;">
      <h3 class="serif" style="font-size: 64px; font-weight: 900; color: {color}; margin-bottom: 12px; line-height: 1.1; letter-spacing: -0.02em;">
        {name}
      </h3>
      <p class="sans" style="font-size: 24px; color: #AAAAAA; line-height: 1.5; letter-spacing: -0.01em; margin-bottom: 8px;">
        {highlighted_reason}
      </p>
      <p class="sans" style="font-size: 18px; color: #555555; letter-spacing: -0.01em;">
        {example_stocks}
      </p>
    </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS["bg"]};">
  <div class="micro-brand">SIGNALFEED</div>

  <!-- Header -->
  <div style="position: absolute; top: 40px; left: 40px; display: flex; align-items: center; gap: 16px;">
    <h2 class="serif" style="font-size: 52px; font-weight: 900; color: {color};">
      {label}
    </h2>
  </div>

  <!-- Sector cards (stacked with gaps) -->
  {sectors_html}

  <!-- Bottom FACT box -->
  <div style="position: absolute; bottom: 40px; left: 40px; right: 40px; background: {self.COLORS["surface"]}; padding: 24px; border-radius: 8px;">
    <p class="sans" style="font-size: 12px; font-weight: 700; letter-spacing: 0.15em; color: {color}; margin-bottom: 8px;">
      FACT /
    </p>
    <p class="sans" style="font-size: 20px; color: #AAAAAA; line-height: 1.5; letter-spacing: -0.01em;">
      {self._highlight_numbers(fact, color)}
    </p>
  </div>
</div>
"""

    def _generate_slide5_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 5: Conclusion — 심플 + 임팩트"""
        title = slide_data.get("title", "오늘의 핵심")
        summaries = slide_data.get("summaries", [])
        watch_point = slide_data.get("watch_point", "")
        cta = slide_data.get("cta", "더 궁금하다면 댓글에 '분석' 남겨주세요")
        cta_sub = slide_data.get("cta_sub", "→ 상세 리포트 DM으로 드립니다")

        # 3 summary blocks (full width, stacked)
        summaries_html = ""
        signal_colors = {"bullish": self.COLORS["bullish"], "bearish": self.COLORS["bearish"], "neutral": self.COLORS["neutral"]}

        for i, summary in enumerate(summaries):
            signal = summary.get("signal", "neutral")
            text = summary.get("text", "")
            color = signal_colors.get(signal, self.COLORS["neutral"])
            y_pos = 200 + (i * 110)

            summaries_html += f"""
    <div style="position: absolute; top: {y_pos}px; left: 40px; right: 40px; background: {self.COLORS["surface"]}; padding: 28px 32px; border-left: 8px solid {color}; border-radius: 4px;">
      <p class="sans" style="font-size: 28px; font-weight: 700; color: {self.COLORS["text_primary"]}; line-height: 1.4; letter-spacing: -0.01em;">
        {text}
      </p>
    </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS["bg"]};">
  <div class="micro-brand">SIGNALFEED</div>

  <!-- Title -->
  <div style="position: absolute; top: 40px; left: 40px;">
    <h2 class="serif" style="font-size: 64px; font-weight: 900; color: {self.COLORS["text_primary"]};">
      {title}
    </h2>
  </div>

  <!-- 3 summary blocks (full width) -->
  {summaries_html}

  <!-- Watch point box -->
  <div style="position: absolute; top: 570px; left: 40px; right: 40px; background: {self.COLORS["card_bg"]}; border-left: 4px solid {self.COLORS["bullish"]}; padding: 28px; border-radius: 8px;">
    <p class="sans" style="font-size: 12px; font-weight: 700; letter-spacing: 0.1em; color: {self.COLORS["bullish"]}; margin-bottom: 8px;">
      주목 포인트
    </p>
    <p class="sans" style="font-size: 22px; color: #AAAAAA; line-height: 1.5; letter-spacing: -0.01em;">
      {watch_point}
    </p>
  </div>

  <!-- CTA block (inverted, green bg) -->
  <div style="position: absolute; bottom: 120px; left: 40px; right: 40px; background: {self.COLORS["bullish"]}; padding: 28px; border-radius: 8px;">
    <p class="sans" style="font-size: 26px; font-weight: 700; color: #000000; margin-bottom: 6px; letter-spacing: -0.01em;">
      {cta}
    </p>
    <p class="sans" style="font-size: 20px; font-weight: 700; color: #000000; letter-spacing: -0.01em;">
      {cta_sub}
    </p>
  </div>

  <!-- Disclaimer -->
  <p style="position: absolute; bottom: 40px; left: 40px; right: 40px; text-align: center; font-size: 13px; color: #333333;">
    본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다
  </p>
</div>
"""

    def screenshot_slides(self, html_path: str, output_dir: str) -> List[str]:
        """
        Take screenshots of all 5 slides using Playwright

        Args:
            html_path: Path to HTML file
            output_dir: Output directory for PNGs

        Returns:
            List of generated PNG paths
        """
        os.makedirs(output_dir, exist_ok=True)

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": self.WIDTH, "height": self.HEIGHT})

                # Load HTML
                page.goto(f"file://{os.path.abspath(html_path)}")

                # Wait for fonts to load
                page.wait_for_timeout(2000)

                # Screenshot each slide
                png_paths = []
                for i in range(1, 6):
                    selector = f"#slide-{i}"
                    slide_path = os.path.join(output_dir, f"slide_{i}.png")

                    page.locator(selector).screenshot(path=slide_path, timeout=30000)
                    png_paths.append(slide_path)
                    logger.info(f"Slide {i} saved: {slide_path}")

                browser.close()
                logger.info(f"All 5 slides saved to {output_dir}")
                return png_paths

        except Exception as e:
            logger.error(f"Playwright screenshot failed: {e}")
            return []

    def generate_all_slides(self, script: Dict, pexels_image_path: str, output_dir: str) -> List[str]:
        """
        Generate all 5 slides for a script

        Args:
            script: Instagram script from content_gen.py
            pexels_image_path: Path to Pexels cover image
            output_dir: Output directory for cards

        Returns:
            List of generated PNG paths
        """
        cluster_id = script.get("cluster_id", "unknown")

        # Generate HTML
        html = self.generate_html(script, pexels_image_path)

        # Save HTML to temp file
        temp_dir = "data/temp"
        os.makedirs(temp_dir, exist_ok=True)
        html_path = os.path.join(temp_dir, f"card_{cluster_id}.html")

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"HTML saved: {html_path}")

        # Screenshot
        png_paths = self.screenshot_slides(html_path, output_dir)

        return png_paths

    def run(self, scripts_path: str = "data/3_generated/scripts.json") -> Dict[str, List[str]]:
        """
        Full pipeline: load scripts → generate cards for all clusters

        Args:
            scripts_path: Path to scripts JSON

        Returns:
            Dict mapping cluster_id to list of PNG paths
        """
        from .image_fetcher import ImageFetcher

        logger.info("=" * 70)
        logger.info("SignalFeed Card Generation Started (AIMing Style)")
        logger.info("=" * 70)

        # Load scripts
        with open(scripts_path, 'r', encoding='utf-8') as f:
            scripts = json.load(f)

        logger.info(f"Loaded {len(scripts)} scripts")

        # Initialize image fetcher
        fetcher = ImageFetcher()

        # Generate cards
        all_cards = {}

        for script_data in scripts:
            cluster_id = script_data.get("cluster_id", "unknown")
            instagram_script = script_data.get("instagram", {})

            # Get Pexels keyword
            pexels_keyword = instagram_script.get("pexels_keyword", "financial district skyscraper aerial")

            # Fetch Pexels image
            logger.info(f"Fetching Pexels image: {pexels_keyword}")
            pexels_image = fetcher.fetch(pexels_keyword, orientation="landscape")

            if not pexels_image:
                logger.warning(f"Failed to fetch image for {pexels_keyword}. Using fallback.")
                pexels_image = fetcher.fetch("global economy finance business", orientation="landscape")

            # Save image to temp file
            image_path = f"data/temp/pexels_{cluster_id}.jpg"
            pexels_image.save(image_path, "JPEG", quality=95)
            logger.info(f"Saved Pexels image: {image_path}")

            # Generate cards
            output_dir = f"data/4_cards/cluster_{cluster_id}"
            png_paths = self.generate_all_slides(instagram_script, image_path, output_dir)

            all_cards[str(cluster_id)] = png_paths
            logger.info(f"Cluster {cluster_id}: {len(png_paths)} cards generated")

        logger.info("=" * 70)
        logger.info(f"Card Generation Complete: {len(all_cards)} clusters")
        logger.info("=" * 70)

        return all_cards


if __name__ == "__main__":
    generator = HTMLCardGenerator()

    if os.path.exists("data/3_generated/scripts.json"):
        cards = generator.run()
        logger.info(f"Generated cards for {len(cards)} clusters")
    else:
        logger.warning("No scripts found. Run content_gen first.")
