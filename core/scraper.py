"""
Core web-scraping primitives: DDG search via ddgs library,
page fetching, metadata extraction, and polite rate-limiting.
"""

import asyncio
import re
import time

import aiohttp
from bs4 import BeautifulSoup
from ddgs import DDGS

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class RateLimiter:
    """Ensure at least `delay` seconds between consecutive calls."""

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self._last = 0.0

    async def wait(self):
        elapsed = time.monotonic() - self._last
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed)
        self._last = time.monotonic()


def search_ddg(query: str, max_results: int = 10) -> list[dict]:
    """
    Search DuckDuckGo via ddgs library.
    Returns list of {title, url, snippet}.
    Synchronous — run in executor if needed.
    """
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))
        return [
            {"title": r["title"], "url": r["href"], "snippet": r.get("body", "")}
            for r in raw
        ]
    except Exception as exc:
        print(f"  [!] DDG search failed: {exc}")
        return []


async def fetch_page(url: str, session: aiohttp.ClientSession) -> str | None:
    """Download a page; return HTML text or None on failure."""
    try:
        async with session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=12),
            allow_redirects=True,
        ) as resp:
            if resp.status == 200:
                ct = resp.headers.get("Content-Type", "")
                if "text/html" in ct:
                    return await resp.text()
    except Exception:
        pass
    return None


async def extract_page_info(html: str | None, url: str) -> dict:
    """Pull metadata from a page's HTML. Returns {description, emails, has_careers}."""
    result = {"description": "", "emails": [], "has_careers": False}
    if not html:
        return result

    soup = BeautifulSoup(html, "html.parser")

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        desc = meta["content"].strip()
        if len(desc) > 10:
            result["description"] = desc[:400]

    raw_emails = re.findall(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", html
    )
    generic = {
        "support", "info", "admin", "contact", "sales", "billing",
        "hello", "noreply", "no-reply", "webmaster", "postmaster",
    }
    unique = []
    for e in raw_emails:
        prefix = e.split("@")[0].lower()
        if prefix not in generic and e not in unique:
            if not re.search(r"[;&<>#]", e) and not e.endswith("."):
                if "u003" not in e and "u002" not in e:
                    tld = e.split(".")[-1]
                    if len(tld) >= 2 and tld.isalpha():
                        unique.append(e)
        if len(unique) >= 5:
            break
    result["emails"] = unique

    career_words = {"career", "hiring", "job", "join", "vacanc", "work with us"}
    for a_tag in soup.find_all("a", href=True):
        text = a_tag.get_text(strip=True).lower()
        href = a_tag["href"].lower()
        if any(w in text for w in career_words) or any(w in href for w in career_words):
            result["has_careers"] = True
            break

    return result
