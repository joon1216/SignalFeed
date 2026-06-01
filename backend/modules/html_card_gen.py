"""
SignalFeed HTML Card Generator
HTML + Playwright 방식으로 Instagram 카드 생성 (Hallmark + Taste Skill 준수)
"""

import os
import json
import logging
from typing import List, Dict
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HTMLCardGenerator:
    """HTML + Playwright 기반 Instagram 카드 생성기"""

    # Canvas dimensions (Instagram 4:5 ratio)
    WIDTH = 1080
    HEIGHT = 1350

    # Color system (signal-based, minimal palette)
    COLORS = {
        "bg_dark": "#111111",
        "bg_surface": "#1A1A1A",
        "bullish": "#00C853",
        "bearish": "#FF3D3D",
        "neutral": "#888888",
        "text_white": "#FAFAFA",
        "text_gray": "#888888",
        "text_dark_gray": "#333333",
    }

    def __init__(self):
        """Initialize HTMLCardGenerator"""
        pass

    def _get_font_css(self) -> str:
        """Get local font CSS"""
        base = os.path.abspath('assets/fonts/noto')
        return f"""
    @font-face {{
        font-family: 'Noto Serif KR';
        font-weight: 900;
        src: url('file://{base}/NotoSerifKR-Black.otf');
    }}
    @font-face {{
        font-family: 'Noto Serif KR';
        font-weight: 700;
        src: url('file://{base}/NotoSerifKR-Bold.otf');
    }}
    @font-face {{
        font-family: 'Noto Sans KR';
        font-weight: 400;
        src: url('file://{base}/NotoSansKR-Regular.otf');
    }}
    @font-face {{
        font-family: 'Noto Sans KR';
        font-weight: 500;
        src: url('file://{base}/NotoSansKR-Medium.otf');
    }}
    @font-face {{
        font-family: 'Noto Sans KR';
        font-weight: 700;
        src: url('file://{base}/NotoSansKR-Bold.otf');
    }}
    """

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
      color: {self.COLORS["text_white"]};
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
      top: 48px;
      left: 60px;
      font-size: 12px;
      letter-spacing: 3px;
      font-weight: 700;
      color: {self.COLORS["bullish"]};
      text-transform: uppercase;
      z-index: 10;
    }}

    /* Slide counter */
    .slide-counter {{
      position: absolute;
      top: 48px;
      right: 60px;
      font-size: 14px;
      color: {self.COLORS["text_gray"]};
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
        """Slide 1: Cover with full bleed image (NO signal badge)"""
        hook_title = slide_data.get("hook_title", "")
        one_line = slide_data.get("one_line", "")
        sources = slide_data.get("sources", ["Reuters", "Bloomberg"])

        sources_text = " · ".join(sources[:3])

        # Use absolute file:// URL for image
        img_url = f"file://{os.path.abspath(image_path)}"

        return f"""
<div class="card" id="slide-{slide_num}" style="background: #000;">
  <!-- Full bleed background image -->
  <div style="position: absolute; inset: 0; background-image: url('{img_url}'); background-size: cover; background-position: center;"></div>

  <!-- Gradient overlay -->
  <div style="position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.5) 40%, rgba(0,0,0,0.85) 70%, rgba(0,0,0,0.95) 100%);"></div>

  <!-- Content -->
  <div class="micro-brand">SIGNALFEED</div>

  <!-- Hook title (y=750px, more dramatic positioning) -->
  <div style="position: absolute; top: 750px; left: 60px; right: 60px;">
    <h1 class="hook-title serif" style="font-size: 80px; font-weight: 900; line-height: 1.15; letter-spacing: -0.03em; color: white; max-width: 900px;">
      {hook_title.replace(chr(10), '<br>')}
    </h1>
  </div>

  <!-- One-line summary -->
  <div style="position: absolute; top: 1040px; left: 60px; right: 60px;">
    <p class="body-text" style="font-size: 18px; letter-spacing: -0.01em; line-height: 1.5; color: rgba(255,255,255,0.7);">
      {one_line}
    </p>
  </div>

  <!-- Sources -->
  <div style="position: absolute; top: 1095px; left: 60px;">
    <p style="font-size: 14px; color: rgba(255,255,255,0.5);">
      {sources_text}
    </p>
  </div>

  <!-- Bottom green line -->
  <div style="position: absolute; bottom: 100px; left: 60px; right: 60px; height: 3px; background: {self.COLORS["bullish"]};"></div>

  <!-- Hashtag badges -->
  <div style="position: absolute; bottom: 40px; right: 60px; display: flex; gap: 8px;">
    <span style="background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.6); padding: 6px 12px; border-radius: 12px; font-size: 12px;">#경제</span>
    <span style="background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.6); padding: 6px 12px; border-radius: 12px; font-size: 12px;">#투자</span>
  </div>
</div>
"""

    def _generate_slide2_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 2: Context (무슨 일이?)"""
        title = slide_data.get("title", "무슨 일이?")
        facts = slide_data.get("facts", [])
        source = slide_data.get("source", "")

        facts_html = ""
        y_pos = 180
        for fact in facts:
            facts_html += f"""
    <div style="position: absolute; top: {y_pos}px; left: 60px; right: 60px; display: flex; gap: 24px;">
      <span style="color: {self.COLORS["bullish"]}; font-size: 24px; font-weight: 700; flex-shrink: 0;">—</span>
      <p class="body-text" style="font-size: 26px; line-height: 1.6; letter-spacing: -0.01em; color: white; max-width: 880px;">
        {fact}
      </p>
    </div>
"""
            y_pos += 220

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS["bg_dark"]};">
  <div class="micro-brand">SIGNALFEED</div>
  <div class="slide-counter">{slide_num}/5</div>

  <!-- Title -->
  <div style="position: absolute; top: 80px; left: 60px;">
    <h2 class="serif" style="font-size: 36px; font-weight: 700; color: {self.COLORS["text_gray"]}; font-style: italic;">
      {title}
    </h2>
  </div>

  <!-- Facts -->
  {facts_html}

  <!-- Source -->
  <p style="position: absolute; bottom: 60px; left: 60px; font-size: 14px; color: {self.COLORS["text_gray"]};">
    출처: {source}
  </p>
</div>
"""

    def _generate_slide3_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 3: Beneficiary (수혜주는?)"""
        return self._generate_sector_slide_html(slide_data, slide_num, "수혜주는?", self.COLORS["bullish"])

    def _generate_slide4_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 4: Victim (주의할 섹터는?)"""
        return self._generate_sector_slide_html(slide_data, slide_num, "주의할 섹터는?", self.COLORS["bearish"])

    def _generate_sector_slide_html(self, slide_data: Dict, slide_num: int, label: str, color: str) -> str:
        """Generate sector slide (beneficiary/victim)"""
        sectors = slide_data.get("sectors", [])
        fact = slide_data.get("fact", "")

        sectors_html = ""
        y_pos = 180
        for sector in sectors:
            name = sector.get("name", "")
            reason = sector.get("reason", "")
            example_stocks = sector.get("example_stocks", [])
            stocks_text = " · ".join(example_stocks[:2]) if example_stocks else ""

            sectors_html += f"""
    <div style="position: absolute; top: {y_pos}px; left: 60px; right: 60px;">
      <h3 class="sector-name serif" style="font-size: 56px; font-weight: 700; color: {color}; margin-bottom: 12px; line-height: 1.2; letter-spacing: -0.02em;">
        {name}
      </h3>
      <p class="body-text" style="font-size: 22px; color: {self.COLORS["text_gray"]}; padding-left: 24px; line-height: 1.5; letter-spacing: -0.01em;">
        {reason}
      </p>
      {"<p style='font-size: 14px; color: #555; padding-left: 24px; margin-top: 6px;'>" + stocks_text + "</p>" if stocks_text else ""}
    </div>
"""
            y_pos += 220

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS["bg_dark"]};">
  <div class="micro-brand">SIGNALFEED</div>
  <div class="slide-counter">{slide_num}/5</div>

  <!-- Label with vertical bar -->
  <div style="position: absolute; top: 80px; left: 60px; display: flex; align-items: center; gap: 20px;">
    <div style="width: 4px; height: 60px; background: {color};"></div>
    <h2 class="sans" style="font-size: 40px; font-weight: 700; color: {color};">
      {label}
    </h2>
  </div>

  <!-- Sectors -->
  {sectors_html}

  <!-- FACT box at bottom -->
  <div style="position: absolute; top: 1150px; left: 60px; right: 60px;">
    <div style="width: 100%; height: 1px; background: #1E1E1E; margin-bottom: 40px;"></div>
    <p style="font-size: 12px; letter-spacing: 1px; color: #444; margin-bottom: 16px; font-weight: 700;">FACT /</p>
    <p class="body-text" style="font-size: 20px; line-height: 1.6; letter-spacing: -0.01em; color: {self.COLORS["text_gray"]}; max-width: 880px;">
      {fact}
    </p>
  </div>
</div>
"""

    def _generate_slide5_html(self, slide_data: Dict, slide_num: int) -> str:
        """Slide 5: Conclusion"""
        title = slide_data.get("title", "오늘의 결론")
        summaries = slide_data.get("summaries", [])
        watch_point = slide_data.get("watch_point", "")
        cta = slide_data.get("cta", "더 궁금하다면 댓글에 '분석' 남겨주세요")
        cta_sub = slide_data.get("cta_sub", "→ 상세 리포트 DM으로 드립니다")

        summaries_html = ""
        for summary in summaries:
            signal = summary.get("signal", "neutral")
            text = summary.get("text", "")
            dot_color = self.COLORS.get(signal, self.COLORS["neutral"])

            summaries_html += f"""
    <div style="display: flex; gap: 24px; margin-bottom: 70px;">
      <div style="width: 12px; height: 12px; border-radius: 50%; background: {dot_color}; margin-top: 12px; flex-shrink: 0;"></div>
      <p style="font-size: 32px; line-height: 1.5; color: white; font-weight: 500; max-width: 920px;">
        {text}
      </p>
    </div>
"""

        watch_point_html = ""
        if watch_point:
            watch_point_html = f"""
  <!-- Watch point box -->
  <div style="background: {self.COLORS["bg_surface"]}; padding: 24px 32px; border-radius: 12px; margin-bottom: 40px;">
    <p style="font-size: 16px; color: {self.COLORS["bullish"]}; font-weight: 700; margin-bottom: 12px;">주목 포인트</p>
    <p style="font-size: 20px; line-height: 1.6; color: white;">
      {watch_point}
    </p>
  </div>
"""

        return f"""
<div class="card" id="slide-{slide_num}" style="background: {self.COLORS["bg_dark"]}; padding: 80px 60px 60px;">
  <div class="micro-brand">SIGNALFEED</div>

  <!-- Title -->
  <h2 class="serif" style="font-size: 64px; font-weight: 900; color: white; margin-bottom: 60px;">
    {title}
  </h2>

  <!-- Summaries -->
  <div style="margin-bottom: 40px;">
    {summaries_html}
  </div>

  {watch_point_html}

  <!-- Horizontal rule -->
  <div style="width: 100%; height: 1px; background: #1E1E1E; margin-bottom: 40px;"></div>

  <!-- CTA -->
  <div style="margin-bottom: 60px;">
    <p style="font-size: 28px; font-weight: 700; color: white; margin-bottom: 12px;">
      {cta}
    </p>
    <p style="font-size: 22px; color: {self.COLORS["bullish"]}; font-weight: 500;">
      {cta_sub}
    </p>
  </div>

  <!-- Disclaimer -->
  <p style="text-align: center; font-size: 13px; color: {self.COLORS["text_dark_gray"]}; position: absolute; bottom: 60px; left: 60px; right: 60px;">
    본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다
  </p>
</div>
"""

    def screenshot_slides(self, html_path: str, cluster_id: str) -> List[str]:
        """
        Screenshot each slide using Playwright with font loading wait

        Args:
            html_path: Path to HTML file
            cluster_id: Cluster ID for output directory

        Returns:
            List of PNG file paths
        """
        from playwright.sync_api import sync_playwright

        output_dir = f"data/6_cards/cluster_{cluster_id}"
        os.makedirs(output_dir, exist_ok=True)

        html_url = f"file://{os.path.abspath(html_path)}"
        output_paths = []

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1350})

            # Load page and wait for network idle
            page.goto(html_url, wait_until="networkidle", timeout=30000)

            # Wait for fonts to load
            page.evaluate("() => document.fonts.ready")

            # Additional wait to ensure rendering complete
            page.wait_for_timeout(2000)

            for i in range(1, 6):
                selector = f"#slide-{i}"
                element = page.query_selector(selector)
                if element:
                    output_path = f"{output_dir}/slide_{i}.png"
                    element.screenshot(path=output_path)
                    output_paths.append(output_path)
                    logger.info(f"✅ Screenshot saved: {output_path}")
                else:
                    logger.warning(f"⚠️ Slide {i} not found: {selector}")

            browser.close()

        return output_paths


    def run(self, scripts_path: str = "data/3_generated/scripts.json") -> Dict:
        """
        Full pipeline: load scripts → generate HTML → screenshot → return paths

        Args:
            scripts_path: Path to scripts JSON

        Returns:
            Dict mapping cluster_id to list of PNG paths
        """
        from backend.modules.image_fetcher import ImageFetcher

        logger.info(f"\n{'='*70}")
        logger.info("6️⃣ Instagram Card Generation (HTML + Playwright)")
        logger.info(f"{'='*70}")

        with open(scripts_path, 'r', encoding='utf-8') as f:
            scripts = json.load(f)

        fetcher = ImageFetcher()
        results = {}

        for script_data in scripts:
            instagram_script = script_data.get("instagram", {})
            cluster_id = instagram_script.get("cluster_id", "unknown")

            # Fetch Pexels image
            pexels_keyword = instagram_script.get("pexels_keyword", "financial district skyscraper aerial")
            image = fetcher.fetch(pexels_keyword)
            if not image:
                image = fetcher._create_fallback_background()

            # Save cover image
            os.makedirs("data/temp", exist_ok=True)
            image_path = f"data/temp/cover_{cluster_id}.jpg"
            image.save(image_path, "JPEG", quality=95)

            # Generate HTML
            html = self.generate_html(instagram_script, image_path)
            html_path = f"data/temp/card_{cluster_id}.html"

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(f"Generated HTML: {html_path}")

            # Screenshot slides
            paths = self.screenshot_slides(html_path, cluster_id)
            results[cluster_id] = paths

            logger.info(f"✅ Cluster {cluster_id}: {len(paths)}장 생성")

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ Card generation complete!")
        logger.info(f"{'='*70}\n")

        return results


if __name__ == "__main__":
    generator = HTMLCardGenerator()
    generator.run()
