import asyncio
import time
from typing import Any, AsyncGenerator
from playwright.async_api import async_playwright, Playwright, BrowserType
import os
from ai_provider import analyze_ui

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
        screenshot_path = f"static/screenshots/home_{browser_type}_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)

        cleaned_html: str = await page.evaluate('''() => {
            const clone = document.documentElement.cloneNode(true);
            const elementsToRemove = clone.querySelectorAll('script, style, svg, path, link, meta, noscript');
            elementsToRemove.forEach(el => el.remove());
            return clone.innerHTML;
        }''')

        await context.close()
        await browser.close()

        ai_report: list[dict[str, Any]] = []
        ai_error: str | None = None
        if ai_model and api_key:
            try:
                ai_report = await analyze_ui(screenshot_path, cleaned_html[:15000], ai_model, api_key)
            except Exception as ai_exc:
                ai_error = str(ai_exc)

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
        for _ in browsers:
            yield await queue.get()
        await asyncio.gather(*tasks, return_exceptions=True)
