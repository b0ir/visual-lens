from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from typing import Optional
import ipaddress
import json
import crawler
import os
from urllib.parse import urlparse
from providers import get_providers_catalog, verify_api_key
from dotenv import load_dotenv

load_dotenv()


def _check_ssrf(url: str) -> None:
    """Raise ValueError if the URL resolves to a private or reserved IP literal."""
    host = urlparse(url).hostname or ""
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError("Requests to private or reserved addresses are not allowed")
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
        # host is a domain name, not an IP literal — allow


app = FastAPI(title="VisualLens API", description="AI-powered Visual Regression Testing Agent")

_allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
_allowed_origins = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

os.makedirs("static/screenshots", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

class AuthRequest(BaseModel):
    url: str
    browser_type: str = "chromium"

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        _check_ssrf(v)
        return v

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

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        _check_ssrf(v)
        return v

    @field_validator("max_pages")
    @classmethod
    def clamp_max_pages(cls, v: int) -> int:
        return max(1, min(v, 50))

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

@app.post("/api/crawl/stream")
async def stream_crawl(req: CrawlRequest):
    async def event_generator():
        try:
            async for result in crawler.stream_headless_crawler(
                req.url, req.max_pages, req.target_browser, req.model_id, req.api_key
            ):
                yield f"data: {json.dumps(result)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'browser': 'unknown', 'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
