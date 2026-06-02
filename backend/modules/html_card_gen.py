"""
SignalFeed HTML Card Generator
Hybrid: Fixed Cover (Pexels) + Gemini Inner Slides
"""

import os
import json
import logging
from typing import List, Dict
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HTMLCardGenerator:
    """Hybrid: Fixed Cover + Gemini Inner Slides"""

    def __init__(self):
        """Initialize HTMLCardGenerator"""
        self.browser = None
        self.playwright = None

        # Import image_fetcher for Pexels
        from backend.modules.image_fetcher import ImageFetcher
        self.image_fetcher = ImageFetcher()

    def _start_browser(self):
        """Start pre-warmed browser instance"""
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        logger.info("✅ Chromium browser started")

    def screenshot_slide(self, html: str, output_path: str):
        """
        Take screenshot of HTML slide

        Args:
            html: Complete HTML string
            output_path: Output PNG path
        """
        if not self.browser:
            self._start_browser()

        context = self.browser.new_context(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=2,  # Retina high-res
        )
        page = context.new_page()
        page.set_content(html, wait_until="networkidle")

        # Wait for fonts to load
        page.evaluate("document.fonts.ready")

        # Screenshot slide div only
        element = page.query_selector("#slide-1") or page.query_selector("div")
        if element:
            element.screenshot(path=output_path)
        else:
            # Fallback: full page
            page.screenshot(path=output_path, full_page=False)

        context.close()

    def generate_cover_html(self, script: dict, pexels_image_path: str) -> str:
        """
        Generate Slide 1 (Cover) HTML with fixed template
        Design: 55% image top + 45% dark text bottom

        Args:
            script: Script dict with hook_title, one_line, sources
            pexels_image_path: Path to Pexels background image

        Returns:
            Complete HTML string
        """
        hook_title = script.get("hook_title", "경제 뉴스")
        one_line = script.get("one_line", "")
        sources = script.get("sources", ["Reuters"])

        # Format date
        date_str = datetime.now().strftime("%Y.%m.%d")

        # Format sources
        sources_str = " · ".join(sources[:3])

        # Convert image to base64 data URI (fix Playwright file:// access issue)
        import os
        import base64

        image_html = ""
        if os.path.exists(pexels_image_path):
            try:
                with open(pexels_image_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode()
                    # Detect image format
                    ext = os.path.splitext(pexels_image_path)[1].lower()
                    mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                    image_html = f'<img src="data:{mime_type};base64,{img_data}" class="absolute inset-0 w-full h-full object-cover" style="object-position: center;"/>'
            except Exception as e:
                logger.warning(f"Failed to encode image: {e}")
                image_html = ""

        # Fallback: no image, just dark background
        if not image_html:
            logger.info("No image available, using dark background only")

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css"/>
  <style>
    body {{ margin: 0; padding: 0; font-family: 'Pretendard', sans-serif; }}
    .word-keep {{ word-break: keep-all; overflow-wrap: break-word; }}
  </style>
</head>
<body>
<div id="slide-1" class="relative w-[1080px] h-[1350px] overflow-hidden" style="background: #0D0D0D;">
  <!-- 배경 이미지 (상단 55%) -->
  <div class="absolute top-0 left-0 right-0 w-full overflow-hidden" style="height: 55%; background: #1A1A1A;">
    {image_html}
  </div>

  <!-- 텍스트 영역 (하단 45%) -->
  <div class="absolute left-0 right-0 w-full" style="top: 55%; height: 45%; background: #0D0D0D; padding: 40px 60px;">
    <!-- 브랜드 -->
    <div class="text-green-400 font-bold text-sm mb-6" style="letter-spacing: 0.2em;">SIGNALFEED</div>

    <!-- 날짜 -->
    <p class="text-gray-500 text-lg mb-8">{date_str} · 글로벌 경제</p>

    <!-- 훅 타이틀 (72px, 2줄) -->
    <h1 class="text-white font-black word-keep mb-6" style="font-size: 72px; line-height: 1.15; font-weight: 900;">{hook_title}</h1>

    <!-- 한줄 요약 -->
    <p class="text-gray-400 word-keep mb-8" style="font-size: 22px; line-height: 1.4;">{one_line}</p>

    <!-- 출처 -->
    <p class="text-gray-600" style="font-size: 16px;">{sources_str}</p>
  </div>

  <!-- 하단 그린 라인 -->
  <div class="absolute bottom-0 left-0 right-0 bg-green-400" style="height: 3px;"></div>
</div>
</body>
</html>"""
        return html

    def generate_cards(self, script: dict, output_dir: str):
        """
        Generate PNG cards from HTML script (hybrid approach)

        Args:
            script: HTML script dict with hook_title, one_line, sources, inner_slides
            output_dir: Output directory for PNG files
        """
        os.makedirs(output_dir, exist_ok=True)
        issue_id = script.get("issue_id", "unknown")

        # Step 1: Fetch Pexels image
        pexels_keyword = script.get("pexels_keyword", "financial district")
        pexels_image = self.image_fetcher.fetch_with_fallback([pexels_keyword])

        # Save Pexels image to temp
        os.makedirs("data/temp", exist_ok=True)
        pexels_path = f"data/temp/pexels_{issue_id}.jpg"
        pexels_image.save(pexels_path, quality=90)
        logger.info(f"Pexels image saved: {pexels_path}")

        # Step 2: Generate Slide 1 (Cover)
        cover_html = self.generate_cover_html(script, os.path.abspath(pexels_path))
        cover_output = f"{output_dir}/slide_1.png"
        self.screenshot_slide(cover_html, cover_output)
        logger.info(f"Slide 1 (Cover) saved: {cover_output}")

        # Step 3: Generate Slides 2~5 (Gemini HTML)
        inner_slides = script.get("inner_slides", [])
        for slide in inner_slides:
            slide_num = slide.get("slide_num", 2)
            html = slide.get("html", "")

            if not html:
                logger.warning(f"Empty HTML for slide {slide_num}, skipping")
                continue

            output_path = f"{output_dir}/slide_{slide_num}.png"
            self.screenshot_slide(html, output_path)
            logger.info(f"Slide {slide_num} saved: {output_path}")

    def close(self):
        """Close browser and playwright"""
        if self.browser:
            self.browser.close()
            logger.info("Browser closed")
        if self.playwright:
            self.playwright.stop()
            logger.info("Playwright stopped")

    def run(self, scripts_path: str = "data/3_generated/scripts.json") -> int:
        """
        Full pipeline: load scripts → generate cards → return count

        Args:
            scripts_path: Input JSON path with HTML scripts

        Returns:
            Number of cards generated
        """
        logger.info("=" * 70)
        logger.info("SignalFeed Card Generation Started (Playwright Screenshot)")
        logger.info("=" * 70)

        # Load scripts
        with open(scripts_path, 'r', encoding='utf-8') as f:
            scripts = json.load(f)

        logger.info(f"Loaded {len(scripts)} HTML scripts")

        # Generate cards
        total_cards = 0
        for script in scripts:
            issue_id = script.get("issue_id", "unknown")
            output_dir = f"data/4_cards/cluster_{issue_id}"

            try:
                self.generate_cards(script, output_dir)
                # Count: 1 cover + inner_slides
                slides_count = 1 + len(script.get("inner_slides", []))
                total_cards += slides_count
                logger.info(f"✅ Cluster {issue_id}: {slides_count} slides")
            except Exception as e:
                logger.error(f"❌ Cluster {issue_id} failed: {e}")
                continue

        # Close browser
        self.close()

        logger.info("=" * 70)
        logger.info(f"Card Generation Complete: {total_cards} cards")
        logger.info("=" * 70)

        return total_cards


if __name__ == "__main__":
    generator = HTMLCardGenerator()

    if os.path.exists("data/3_generated/scripts.json"):
        count = generator.run()
        logger.info(f"Generated {count} cards")
    else:
        logger.warning("No scripts found. Run content_gen first.")
