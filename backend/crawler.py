import asyncio
import logging
import re
import time
from typing import Any, AsyncGenerator
from playwright.async_api import async_playwright, Playwright, BrowserType
import os
from ai_provider import analyze_ui

logger = logging.getLogger(__name__)

AUTH_FILE = "auth.json"


def get_browser_engine(p: Playwright, browser_type: str) -> BrowserType:
    """Return the Playwright BrowserType matching the requested engine name."""
    if browser_type.lower() == "firefox":
        return p.firefox
    elif browser_type.lower() in ["webkit", "safari"]:
        return p.webkit
    else:
        return p.chromium


LOGIN_TIMEOUT_SECONDS = int(os.environ.get("LOGIN_TIMEOUT_SECONDS", "300"))  # 5-minute default; enough for manual login flows

_INVALID_SELECTOR_SUFFIX = re.compile(
    r":(?:contains|visible|hidden|has-text|icontains|selected|checked)\([^)]*\).*$"
)


def _repair_selector(selector: str) -> str | None:
    """Strip a trailing jQuery-only pseudo-selector the model may have hallucinated,
    returning a plain-CSS prefix, or None if there was nothing to strip."""
    repaired = _INVALID_SELECTOR_SUFFIX.sub("", selector).strip()
    if not repaired or repaired == selector:
        return None
    return repaired


async def launch_interactive_login(url: str, browser_type: str = "chromium") -> dict[str, str]:
    """Open a headed browser for manual login and save the auth state to disk."""
    async with async_playwright() as p:
        engine = get_browser_engine(p, browser_type)
        browser = await engine.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url)

        elapsed = 0
        while browser.is_connected():
            await asyncio.sleep(1)
            elapsed += 1
            if elapsed >= LOGIN_TIMEOUT_SECONDS:
                await browser.close()
                return {"status": "error", "message": f"Login timed out after {LOGIN_TIMEOUT_SECONDS} seconds."}

        await context.storage_state(path=AUTH_FILE)
        return {"status": "success", "message": "Authentication saved successfully."}


async def _get_element_bbox(page: Any, selector: str) -> dict[str, Any] | None:
    """Instantly lookup an element's bounding rectangle via JS DOM evaluation,
    returning None immediately if the selector is invalid.
    Returns DOM existence, element coordinates, and page dimensions for crop clamping."""
    try:
        return await page.evaluate(
            """(sel) => {
                try {
                    const el = document.querySelector(sel);
                    const pageWidth = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0, 1280);
                    const pageHeight = Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0, 720);
                    if (!el) {
                        return { exists: false, pageWidth, pageHeight };
                    }
                    const rect = el.getBoundingClientRect();
                    return {
                        exists: true,
                        x: rect.left + window.scrollX,
                        y: rect.top + window.scrollY,
                        width: rect.width,
                        height: rect.height,
                        pageWidth,
                        pageHeight
                    };
                } catch (e) {
                    return null;
                }
            }""",
            selector,
        )
    except Exception:
        return None


async def _crawl_single_browser(
    p: Playwright,
    start_url: str,
    browser_type: str,
    ai_model: str,
    api_key: str,
) -> dict[str, Any]:
    """Capture a screenshot and run AI analysis for one browser engine."""
    engine = get_browser_engine(p, browser_type)
    try:
        browser = await engine.launch(headless=True)
        if os.path.exists(AUTH_FILE):
            context = await browser.new_context(storage_state=AUTH_FILE)
        else:
            context = await browser.new_context()

        page = await context.new_page()
        timestamp = int(time.time())
        await page.goto(start_url, wait_until="networkidle")

        os.makedirs("static/screenshots", exist_ok=True)
        safe_browser = re.sub(r"[^a-z0-9]", "_", browser_type.lower())
        screenshot_path = f"static/screenshots/home_{safe_browser}_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)

        cleaned_html: str = await page.evaluate('''() => {
            const clone = document.documentElement.cloneNode(true);
            const elementsToRemove = clone.querySelectorAll('script, style, svg, path, link, meta, noscript');
            elementsToRemove.forEach(el => el.remove());
            return clone.innerHTML;
        }''')

        ai_report: list[dict[str, Any]] = []
        ai_error: str | None = None
        if ai_model and api_key:
            try:
                ai_report = await analyze_ui(screenshot_path, cleaned_html[:15000], ai_model, api_key)
            except Exception as ai_exc:
                ai_error = str(ai_exc)

        _CROP_PADDING = 30
        valid_report: list[dict[str, Any]] = []

        for idx, bug in enumerate(ai_report):
            selector = (bug.get("element_selector") or "").strip()
            if not selector:
                continue

            bbox_data = await _get_element_bbox(page, selector)

            if not bbox_data or not bbox_data.get("exists"):
                repaired = _repair_selector(selector)
                if repaired:
                    bbox_data = await _get_element_bbox(page, repaired)

            # Filter out hallucinated selectors that do not exist in the actual DOM
            if not bbox_data or not bbox_data.get("exists"):
                logger.warning("Filtering out hallucinated bug with selector %r (not found in DOM)", selector)
                continue

            valid_report.append(bug)

            page_w = float(bbox_data.get("pageWidth", 1280))
            page_h = float(bbox_data.get("pageHeight", 720))
            rect_w = float(bbox_data.get("width", 0))
            rect_h = float(bbox_data.get("height", 0))

            if rect_w > 0 and rect_h > 0:
                raw_x = float(bbox_data.get("x", 0))
                raw_y = float(bbox_data.get("y", 0))

                # Clamp clip box coordinates strictly within page document boundaries
                x = max(0.0, min(raw_x - _CROP_PADDING, page_w - 10))
                y = max(0.0, min(raw_y - _CROP_PADDING, page_h - 10))
                w = max(10.0, min(rect_w + 2 * _CROP_PADDING, page_w - x))
                h = max(10.0, min(rect_h + 2 * _CROP_PADDING, page_h - y))

                crop_path = f"static/screenshots/crop_{safe_browser}_{timestamp}_{idx}.png"
                try:
                    await page.screenshot(path=crop_path, clip={"x": x, "y": y, "width": w, "height": h})
                    bug["screenshot_crop"] = crop_path
                except Exception as e:
                    logger.warning("Crop screenshot capture failed for selector %r: %s", selector, e)
            elif bug.get("category") == "hidden":
                logger.debug("No bounding box for selector %r — expected for a 'hidden' bug", selector)

        ai_report = valid_report

        await context.close()
        await browser.close()

        return {
            "status": "success",
            "browser": browser_type,
            "screenshot": screenshot_path,
            "dom_snippet": cleaned_html[:500],
            "ai_report": ai_report,
            **({"ai_error": ai_error} if ai_error else {}),
        }
    except Exception as e:
        return {
            "status": "error",
            "browser": browser_type,
            "error": str(e),
        }


async def run_headless_crawler(
    start_url: str,
    max_pages: int,
    target_browser: str,
    ai_model: str,
    api_key: str,
) -> dict[str, Any]:
    """Crawl start_url across the requested browser(s) and return all results."""
    async with async_playwright() as p:
        browsers = (
            ["chromium", "firefox", "webkit"]
            if target_browser.lower() == "all"
            else [target_browser.lower()]
        )
        tasks = [_crawl_single_browser(p, start_url, b, ai_model, api_key) for b in browsers]
        results = await asyncio.gather(*tasks)
        return {"status": "success", "results": results}


async def stream_headless_crawler(
    start_url: str,
    max_pages: int,
    target_browser: str,
    ai_model: str,
    api_key: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """Yield each browser result as soon as it completes rather than waiting for all."""
    async with async_playwright() as p:
        browsers = (
            ["chromium", "firefox", "webkit"]
            if target_browser.lower() == "all"
            else [target_browser.lower()]
        )
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def crawl_and_enqueue(browser_type: str) -> None:
            result = await _crawl_single_browser(p, start_url, browser_type, ai_model, api_key)
            await queue.put(result)

        tasks = [asyncio.create_task(crawl_and_enqueue(b)) for b in browsers]

        initial: dict[str, dict[str, Any]] = {}
        for _ in browsers:
            result = await queue.get()
            initial[result["browser"]] = result
            yield result
        await asyncio.gather(*tasks, return_exceptions=True)

        # If running multiple browsers and at least one found bugs but another found none,
        # retry the zero-bug browsers once — model inconsistency can cause false "no bugs".
        if len(browsers) > 1:
            any_bugs = any(
                bool(r.get("ai_report"))
                for r in initial.values()
                if r.get("status") == "success"
            )
            if any_bugs:
                to_retry = [
                    b for b, r in initial.items()
                    if r.get("status") == "success" and not r.get("ai_report")
                ]
                for b in to_retry:
                    yield {"status": "retrying", "browser": b}

                retry_tasks = [asyncio.create_task(crawl_and_enqueue(b)) for b in to_retry]
                for _ in to_retry:
                    yield await queue.get()
                await asyncio.gather(*retry_tasks, return_exceptions=True)
