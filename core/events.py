
"""
Networking event discovery via DDG with refreshment signal detection.
"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

import aiohttp

from .scraper import USER_AGENT, RateLimiter, search_ddg

REFRESHMENT_KEYWORDS = [
    "refreshment", "networking drinks", "high tea", "buffet",
    "dinner included", "happy hour", "hors d'oeuvres", "cocktail",
    "catered", "open bar", "coffee break", "lunch provided",
    "breakfast included", "wine", "canap\u00e9s", "finger food",
]


async def scrape_networking_events(city: str, max_results: int) -> list:
    limiter = RateLimiter(delay=2.5)
    queries = [
        f"{city} networking events mixer",
        f"{city} business networking meetup",
    ]
    executor = ThreadPoolExecutor(max_workers=1)
    per_query = max(4, max_results // 2)
    seen = set()
    all_results = []

    loop = asyncio.get_event_loop()
    for q in queries:
        await limiter.wait()
        print(f"  Searching: {q}")
        results = await loop.run_in_executor(executor, lambda q=q: search_ddg(q, per_query))
        for r in results:
            if r["url"] not in seen and len(all_results) < max_results:
                seen.add(r["url"])
                all_results.append(r)
        if len(all_results) >= max_results:
            break

    executor.shutdown(wait=False)
    print(f"  Found {len(all_results)} event listings.")
    events = []

    for sr in all_results:
        combined = (sr["title"] + " " + sr["snippet"]).lower()
        signal = "None detected"
        for kw in REFRESHMENT_KEYWORDS:
            if kw in combined:
                signal = f"Mentions '{kw}'"
                break

        events.append({
            "name": sr["title"],
            "venue": city,
            "date": _guess_date(sr["snippet"]),
            "url": sr["url"],
            "refreshment_signal": signal,
            "description": sr["snippet"],
        })

    return events


def _guess_date(text: str) -> str:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",
        r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group()
    return "TBA"
