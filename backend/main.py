from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from typing import Optional
import ipaddress
import json
import logging
import socket
import crawler
import os
from pathlib import Path
from urllib.parse import urlparse
from providers import get_providers_catalog, verify_api_key
from dotenv import load_dotenv

# Load the single repo-root .env regardless of the working directory.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("visuallens")

_SSRF_ERROR = "Requests to private or reserved addresses are not allowed"


def _is_blocked_ip(ip_str: str) -> bool:
    """True if the address is private, loopback, reserved, or link-local."""
    ip = ipaddress.ip_address(ip_str)
    return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local


def _check_ssrf(url: str) -> None:
    """Raise ValueError if the URL's host is, or resolves to, a private/reserved address.

    Covers both IP literals and domain names. Resolving the hostname and checking
    every returned address defends against DNS-rebinding to internal or
    cloud-metadata endpoints.
    """
    host = (urlparse(url).hostname or "").strip()
    if not host:
        raise ValueError("Invalid URL: missing host")

    # IP literal supplied directly.
    try:
        if _is_blocked_ip(host):
            raise ValueError(_SSRF_ERROR)
        return
    except ValueError as exc:
        if _SSRF_ERROR in str(exc):
            raise
        # Not an IP literal — fall through to hostname resolution.

    # localhost and its subdomains never reach DNS but must still be blocked.
    lowered = host.lower()
    if lowered == "localhost" or lowered.endswith(".localhost"):
        raise ValueError(_SSRF_ERROR)

    try:
        resolved = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Unresolvable host — let the browser surface the failure naturally.
        return
    for info in resolved:
        if _is_blocked_ip(info[4][0]):
            raise ValueError(_SSRF_ERROR)


app = FastAPI(
    title="VisualLens API",
    description="AI-powered Visual Regression Testing Agent",
    version="0.1.0",
)

_allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
_allowed_origins = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


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
            logger.error("Crawl stream failed: %s", e, exc_info=True)
            error_payload = {
                "status": "error",
                "browser": "unknown",
                "error": "An error occurred during crawling. See backend logs for details.",
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
