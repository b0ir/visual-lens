from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import crawler
import os

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

class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 5
    target_browser: str = "all"

@app.get("/")
def read_root():
    return {"message": "Welcome to VisualLens API"}

@app.post("/api/auth/start")
async def start_interactive_auth(req: AuthRequest):
    result = await crawler.launch_interactive_login(req.url)
    return result

@app.post("/api/crawl/start")
async def start_crawl(req: CrawlRequest):
    result = await crawler.run_headless_crawler(req.url, req.max_pages, req.target_browser)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
