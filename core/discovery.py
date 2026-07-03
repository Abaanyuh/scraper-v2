"""
Company discovery via DuckDuckGo search + per-page enrichment.
"""

import asyncio
import sqlite3
import os

import aiohttp

from .scraper import (
    USER_AGENT,
    RateLimiter,
    search_ddg,
    fetch_page,
    extract_page_info,
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "discovered.db")


# ---------------------------------------------------------------------------
# Duplicate cache (SQLite)
# ---------------------------------------------------------------------------

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS scraped (url TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()


def _is_scraped(url: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT 1 FROM scraped WHERE url=?", (url,)).fetchone()
    conn.close()
    return row is not None


def _mark_scraped(url: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO scraped(url) VALUES(?)", (url,))
    conn.commit()
    conn.close()


def clear_cache():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


# ---------------------------------------------------------------------------
# Discovery run
# ---------------------------------------------------------------------------

async def run_company_discovery(query: str, max_results: int) -> list[dict]:
    """
    Search DuckDuckGo for *query*, visit each result page, and extract
    company metadata + contact emails.
    """
    _init_db()
    limiter = RateLimiter(delay=2.0)

    async with aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT},
        timeout=aiohttp.ClientTimeout(total=20),
    ) as session:

        # Step 1 — search
        print(f"  Searching DDG for '{query}' …")
        search_results = await search_ddg(query, max_results, session)
        print(f"  Found {len(search_results)} results.")

        if not search_results:
            return []

        # Step 2 — enrich each company
        companies: list[dict] = []
        for i, sr in enumerate(search_results, 1):
            url = sr["url"]
            if _is_scraped(url):
                print(f"  [{i}/{len(search_results)}] SKIP (cached)  {url}")
                continue

            await limiter.wait()
            print(f"  [{i}/{len(search_results)}] Fetching {url[:80]} …")
            html = await fetch_page(url, session)

            info = await extract_page_info(html, url)
            company = {
                "url": url,
                "name": info["name"],
                "description": info.get("description", sr.get("snippet", "")),
                "industry": query,
                "industry_hint": info.get("industry_hint", ""),
                "size": _guess_size(info),
                "hiring_signals": "Yes" if info["has_careers"] else "No",
                "contacts": info["emails"],
            }
            companies.append(company)
            _mark_scraped(url)

        return companies


def _guess_size(info: dict) -> str:
    """Crude heuristic — not reliable, but better than hardcoded 'Mid'."""
    desc = (info.get("description", "") + " " + info.get("industry_hint", "")).lower()
    large_words = {"enterprise", "global", "fortune", "multinational", "1000+"}
    small_words = {"startup", "small business", "boutique", "freelance", "solo"}
    if any(w in desc for w in large_words):
        return "Large"
    if any(w in desc for w in small_words):
        return "Small"
    return "Mid"
