from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import crawler
import os
from providers import get_providers_catalog, verify_api_key

app = FastAPI(title="VisualLens API", description="AI-powered Visual Regression Testing Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/screenshots", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

class AuthRequest(BaseModel):
    url: str
    browser_type: str = "chromium"

class VerifyKeyRequest(BaseModel):
    provider_id: str
    api_key: str

class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 5
    target_browser: str = "all"
    provider_id: str = ""
    api_key: str = ""
    model_id: str = ""

@app.get("/")
def read_root():
    return {"message": "Welcome to VisualLens API"}

@app.get("/api/providers")
def get_providers():
    """Return the full provider catalog with vision models."""
    return get_providers_catalog()

@app.post("/api/providers/verify")
async def verify_provider_key(req: VerifyKeyRequest):
    """Verify an API key against a provider."""
    result = await verify_api_key(req.provider_id, req.api_key)
    return result

@app.post("/api/auth/start")
async def start_interactive_auth(req: AuthRequest):
    result = await crawler.launch_interactive_login(req.url, req.browser_type)
    return result

@app.post("/api/crawl/start")
async def start_crawl(req: CrawlRequest):
    result = await crawler.run_headless_crawler(
        req.url, req.max_pages, req.target_browser, req.model_id, req.api_key
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
