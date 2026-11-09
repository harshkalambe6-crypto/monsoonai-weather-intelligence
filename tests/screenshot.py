"""MONSOONAI dashboard — screenshot capture (Phase 5, local only).

Opens the locally running Streamlit server in headless Chromium and
screenshots every page at desktop width (1440x900) and the Overview +
Rainfall Prediction pages at mobile width (390x844).

Prerequisites: the Streamlit server must be running on
http://localhost:8501 (streamlit run app/app.py) and Chromium must be
installed (playwright install chromium).

Run:  ~/workspace/monsoonai-venv/bin/python tests/screenshot.py
Output: docs/screenshots/*.png
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT = PROJECT_ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://localhost:8501"
PAGES = [
    ("01-overview", "Overview"),
    ("02-prediction", "Rainfall Prediction"),
    ("03-historical", "Historical Analysis"),
    ("04-extreme", "Extreme Rainfall"),
    ("05-performance", "Model Performance"),
    ("06-methodology", "Data & Methodology"),
]
MOBILE_PAGES = ["01-overview", "02-prediction"]


WAIT_TEXT = {
    "01-overview": "Headline results",
    "02-prediction": "Make a prediction",
    "03-historical": "How the 9,132 days classify",
    "04-extreme": "Dedicated heavy-rain classifier",
    "05-performance": "Regression — next-day rainfall amount",
    "06-methodology": "Data sources",
}


def screenshot_page(slug, label, width, height, suffix):
    """Navigate to the app, click the sidebar radio option, screenshot."""
    from playwright.sync_api import sync_playwright

    out_path = OUT / f"{slug}-{suffix}.png"
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": width, "height": height})
        pg.goto(BASE_URL, wait_until="networkidle")
        # Wait for the app to finish loading (first load takes ~6 s
        # while the models load) and for the page content to appear.
        pg.wait_for_selector("text=MONSOONAI", timeout=60000)
        pg.wait_for_selector(f"text={WAIT_TEXT['01-overview']}",
                             timeout=120000)
        if slug != "01-overview":
            if width < 500:
                # On mobile the sidebar starts collapsed: expand it first.
                pg.locator('[data-testid="stExpandSidebarButton"]').click()
                time.sleep(1)
            pg.get_by_text(label, exact=True).first.click()
            pg.wait_for_selector(f"text={WAIT_TEXT[slug]}",
                                 timeout=120000)
            time.sleep(2)  # let charts finish drawing
            if width < 500:
                # Close the sidebar overlay so the page content is visible.
                pg.get_by_label("Collapse sidebar").click()
                time.sleep(1)
        pg.mouse.move(10, 10)
        pg.screenshot(path=str(out_path), full_page=True)
        browser.close()
    print(f"saved {out_path} ({out_path.stat().st_size // 1024} KB)")
    return out_path


def main():
    for slug, label in PAGES:
        screenshot_page(slug, label, 1440, 900, "desktop")
    for slug, label in PAGES:
        if slug in MOBILE_PAGES:
            screenshot_page(slug, label, 390, 844, "mobile")
    print("DONE — screenshots in", OUT)


if __name__ == "__main__":
    main()
