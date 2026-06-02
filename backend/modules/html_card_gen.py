"""
SignalFeed HTML Card Generator
Playwright Screenshot Only (HTML from Gemini)
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
    """Playwright 기반 HTML → PNG 스크린샷 생성기"""

    def __init__(self):
        """Initialize HTMLCardGenerator"""
        self.browser = None
        self.playwright = None

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

    def generate_cards(self, script: dict, output_dir: str):
        """
        Generate PNG cards from HTML script

        Args:
            script: HTML script dict with slides
            output_dir: Output directory for PNG files
        """
        slides = script.get("slides", [])
        os.makedirs(output_dir, exist_ok=True)

        for slide in slides:
            slide_num = slide.get("slide_num", 1)
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
                slides_count = len(script.get("slides", []))
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
