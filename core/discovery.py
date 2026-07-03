
"""
Company discovery via DDG multi-query search + per-page enrichment.
Uses ddgs library for reliable search.
"""

import asyncio
import sqlite3
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import aiohttp

from .scraper import (
    USER_AGENT,
    RateLimiter,
    search_ddg,
    fetch_page,
    extract_page_info,
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "discovered.db")


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
    p = Path(DB_PATH)
    if p.exists():
        p.unlink()


def _build_queries(keyword: str, n: int) -> list:
    per_query = max(4, n // 2)
    return [
        (f'"{keyword}" company', per_query),
        (f"{keyword} company website", per_query),
    ]


async def run_company_discovery(query: str, max_results: int) -> list:
    _init_db()
    limiter = RateLimiter(delay=3.0)
    executor = ThreadPoolExecutor(max_workers=1)
    queries = _build_queries(query, max_results)
    seen_urls = set()
    all_results = []

    for q, n in queries:
        await limiter.wait()
        print(f"  Searching: {q}")
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(executor, lambda q=q, n=n: search_ddg(q, n))
        for r in results:
            if r["url"] not in seen_urls and len(all_results) < max_results:
                seen_urls.add(r["url"])
                all_results.append(r)
        if len(all_results) >= max_results:
            break

    executor.shutdown(wait=False)
    print(f"  Found {len(all_results)} unique results.")

    if not all_results:
        return []

    async with aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT},
        timeout=aiohttp.ClientTimeout(total=20),
    ) as session:

        companies = []
        for i, sr in enumerate(all_results, 1):
            url = sr["url"]
            if _is_scraped(url):
                continue

            company_name = _clean_company_name(sr["title"])
            ddg_desc = sr["snippet"]

            await limiter.wait()
            print(f"  [{i}/{len(all_results)}] {company_name[:50]}")
            html = await fetch_page(url, session)
            info = await extract_page_info(html, url)

            description = info.get("description", "") or ddg_desc
            hiring = "Yes" if info["has_careers"] else _hiring_from_snippet(ddg_desc)
            size = _guess_size(ddg_desc + " " + description)

            companies.append({
                "url": url,
                "name": company_name,
                "description": description,
                "industry": query,
                "size": size,
                "hiring_signals": hiring,
                "contacts": info["emails"],
            })
            _mark_scraped(url)

        return companies


def _clean_company_name(title: str) -> str:
    for s in [" - Wikipedia", " | LinkedIn", " - Crunchbase", " - Home"]:
        if s in title:
            title = title.split(s)[0]
    for sep in [" | ", " - "]:
        if len(title.split(sep)[0]) > 10:
            title = title.split(sep)[0]
    return title.strip()[:120]


def _hiring_from_snippet(text: str) -> str:
    signals = ["hiring", "career", "job opening", "join our team",
               "we're hiring", "now hiring", "vacancy", "apply now"]
    if any(s in text.lower() for s in signals):
        return "Yes (snippet)"
    return "No"


def _guess_size(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["enterprise", "global", "fortune", "multinational"]):
        return "Large"
    if any(w in t for w in ["startup", "small business", "boutique", "early-stage", "seed"]):
        return "Small"
    return "Mid"
