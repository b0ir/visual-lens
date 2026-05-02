import asyncio
from playwright.async_api import async_playwright
import os
from ai_provider import analyze_ui

AUTH_FILE = "auth.json"

def get_browser_engine(p, browser_type: str):
    if browser_type.lower() == "firefox":
        return p.firefox
    elif browser_type.lower() in ["webkit", "safari"]:
        return p.webkit
    else:
        return p.chromium

async def launch_interactive_login(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url)
        
        while browser.is_connected():
            await asyncio.sleep(1)
            
        await context.storage_state(path=AUTH_FILE)
        return {"status": "success", "message": "Authentication saved successfully."}

async def _crawl_single_browser(p, start_url: str, browser_type: str, ai_model: str, api_key: str):
    engine = get_browser_engine(p, browser_type)
    try:
        if os.path.exists(AUTH_FILE):
            browser = await engine.launch(headless=True)
            context = await browser.new_context(storage_state=AUTH_FILE)
        else:
            browser = await engine.launch(headless=True)
            context = await browser.new_context()
            
        page = await context.new_page()
        await page.goto(start_url)
        
        os.makedirs("static/screenshots", exist_ok=True)
        screenshot_path = f"static/screenshots/home_{browser_type}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        
        cleaned_html = await page.evaluate('''() => {
            const clone = document.documentElement.cloneNode(true);
            const elementsToRemove = clone.querySelectorAll('script, style, svg, path, link, meta, noscript');
            elementsToRemove.forEach(el => el.remove());
            return clone.innerHTML;
        }''')
        
        await context.close()
        await browser.close()
        
        # Analyze with AI
        ai_report = []
        if ai_model and api_key:
            # Trim HTML to avoid massive token limits (keep roughly first 15k chars)
            ai_report = await analyze_ui(screenshot_path, cleaned_html[:15000], ai_model, api_key)
        
        return {
            "status": "success",
            "browser": browser_type,
            "screenshot": screenshot_path,
            "dom_snippet": cleaned_html[:500],
            "ai_report": ai_report
        }
    except Exception as e:
        return {
            "status": "error",
            "browser": browser_type,
            "error": str(e)
        }

async def run_headless_crawler(start_url: str, max_pages: int, target_browser: str, ai_model: str, api_key: str):
    async with async_playwright() as p:
        if target_browser.lower() == "all":
            browsers = ["chromium", "firefox", "webkit"]
        else:
            browsers = [target_browser.lower()]
            
        tasks = [_crawl_single_browser(p, start_url, b, ai_model, api_key) for b in browsers]
        results = await asyncio.gather(*tasks)
        return {"status": "success", "results": results}
