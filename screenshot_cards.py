#!/usr/bin/env python3
"""Screenshot Instagram card preview HTML"""

from playwright.sync_api import sync_playwright

def screenshot_card_preview():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1080, 'height': 5400})
        page.goto(f'file:///Users/joon/Documents/GitHub/issuefit_project/frontend/card_preview.html')
        page.screenshot(path='frontend/card_preview.png', full_page=True)
        browser.close()
        print("✅ Screenshot saved to frontend/card_preview.png")

if __name__ == "__main__":
    screenshot_card_preview()
