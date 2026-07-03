"""
Networking event discovery — search DuckDuckGo for city‑specific
business mixers and flag results that mention refreshments.
"""

import asyncio

import aiohttp

from .scraper import USER_AGENT, RateLimiter, search_ddg

REFRESHMENT_KEYWORDS = [
    "refreshment", "networking drinks", "high tea", "buffet",
    "dinner included", "happy hour", "hors d'oeuvres", "cocktail",
    "catered", "open bar", "coffee break", "lunch provided",
    "breakfast included", "wine", "canapés", "finger food",
]


async def scrape_networking_events(city: str, max_results: int) -> list[dict]:
    """
    Search DDG for networking events in *city* and flag refreshment signals.
    """
    limiter = RateLimiter(delay=2.5)
    query = f"{city} networking events business mixer"

    async with aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT},
        timeout=aiohttp.ClientTimeout(total=20),
    ) as session:

        await limiter.wait()
        print(f"  Searching for events in {city} …")
        results = await search_ddg(query, max_results * 2, session)

        events: list[dict] = []
        for sr in results:
            title = sr["title"]
            snippet = sr.get("snippet", "")
            combined = (title + " " + snippet).lower()

            refreshment_signal = "None detected"
            for kw in REFRESHMENT_KEYWORDS:
                if kw in combined:
                    refreshment_signal = f"✅ Mentions '{kw}'"
                    break

            events.append({
                "name": title,
                "venue": city,
                "date": _guess_date(snippet),
                "url": sr["url"],
                "refreshment_signal": refreshment_signal,
            })

            if len(events) >= max_results:
                break

        return events


def _guess_date(text: str) -> str:
    """Try to pull a date-like string from a snippet."""
    import re

    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",                         # 2026-08-15
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",
        r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group()
    return "TBA"
