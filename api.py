from typing import Any
import sys
import asyncio
from fastapi.responses import StreamingResponse
import requests
import io
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.instagram import InstagramStatsScraper

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


app = FastAPI(title="Instagram Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    username: str = Field(..., min_length=1)
    max_posts: int = Field(10, ge=1, le=100)
    headless: bool = False
    exclude_pinned: bool = False


class ScrapeResponse(BaseModel):
    profile: dict[str, Any]
    posts: list[dict[str, Any]]


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/scrape", response_model=ScrapeResponse)
async def scrape_profile(payload: ScrapeRequest):
    username = payload.username.strip().replace("@", "").strip("/")
    if not username:
        raise HTTPException(status_code=400, detail="Username inválido")

    profile_url = f"https://www.instagram.com/{username}/"

    scraper = InstagramStatsScraper(
        profile_url=profile_url,
        max_posts=payload.max_posts,
        exclude_pinned=payload.exclude_pinned,
        headless=payload.headless,
    )

    try:
        result = await scraper.run_as_api()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    
@app.get("/api/profile-image")
def profile_image(url: str):
    r = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0"
    })

    return StreamingResponse(
        io.BytesIO(r.content),
        media_type="image/jpeg"
    )