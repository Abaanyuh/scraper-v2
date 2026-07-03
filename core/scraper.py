"""
Core web-scraping primitives: DuckDuckGo search, page fetching,
metadata extraction, and polite rate-limiting.
"""

import asyncio
import re
import time
from urllib.parse import urlparse, parse_qs

import aiohttp
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
DDG_HTML = "https://html.duckduckgo.com/html/"

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# DuckDuckGo search
# ---------------------------------------------------------------------------

async def search_ddg(
    query: str,
    max_results: int = 10,
    session: aiohttp.ClientSession | None = None,
) -> list[dict]:
    """
    Search DuckDuckGo's HTML (non-JS) endpoint.

    Returns a list of dicts: {title, url, snippet}.
    """
    close = False
    if session is None:
        session = aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=20),
        )
        close = True

    try:
        async with session.get(DDG_HTML, params={"q": query}) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()
    except Exception as exc:
        print(f"  [!] DDG search failed: {exc}")
        return []
    finally:
        if close:
            await session.close()

    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []

    for item in soup.select(".result"):
        title_el = item.select_one(".result__title a")
        snippet_el = item.select_one(".result__snippet")
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        raw_href = title_el.get("href", "")
        url = _extract_ddg_url(raw_href)
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        if url:
            results.append({"title": title, "url": url, "snippet": snippet})

        if len(results) >= max_results:
            break

    return results


def _extract_ddg_url(href: str) -> str:
    """DDG wraps result links in a redirect — extract the real target."""
    from urllib.parse import unquote
    if "uddg=" in href:
        try:
            parsed = urlparse(href, scheme="https")
            qs_params = parse_qs(parsed.query)
            if "uddg" in qs_params:
                return unquote(qs_params["uddg"][0])
        except Exception:
            pass
    return href


# ---------------------------------------------------------------------------
# Page fetching & info extraction
# ---------------------------------------------------------------------------

async def fetch_page(
    url: str,
    session: aiohttp.ClientSession,
) -> str | None:
    """Download a page; return HTML text or None on failure."""
    try:
        async with session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=15),
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
    """
    Pull company metadata from a page's HTML.

    Returns {name, description, industry_hint, emails, has_careers}.
    """
    result = {
        "name": urlparse(url).netloc.replace("www.", ""),
        "description": "",
        "industry_hint": "",
        "emails": [],
        "has_careers": False,
    }
    if not html:
        return result

    soup = BeautifulSoup(html, "html.parser")

    # -- title --
    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)
    result["name"] = title[:120] if title else result["name"]

    # -- meta description --
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        result["description"] = meta["content"][:400]

    # -- industry hint from meta keywords --
    kw = soup.find("meta", attrs={"name": "keywords"})
    if kw and kw.get("content"):
        result["industry_hint"] = kw["content"][:200]

    # -- emails --
    raw_emails = re.findall(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html
    )
    generic = {
        "support", "info", "admin", "contact", "sales", "billing",
        "hello", "noreply", "no-reply", "webmaster", "postmaster",
    }
    unique: list[str] = []
    for e in raw_emails:
        if e.split("@")[0].lower() not in generic and e not in unique:
            unique.append(e)
        if len(unique) >= 5:
            break
    result["emails"] = unique

    # -- hiring signal --
    career_words = {"career", "hiring", "job", "join", "vacanc", "work with us"}
    for a_tag in soup.find_all("a", href=True):
        text = a_tag.get_text(strip=True).lower()
        href = a_tag["href"].lower()
        if any(w in text for w in career_words) or any(w in href for w in career_words):
            result["has_careers"] = True
            break

    return result
