"""
Company enrichment — kept as a thin forwarding layer.
Real enrichment now lives in core/scraper.py (extract_page_info)
and is called directly from discovery.py.
"""

from .scraper import fetch_page, extract_page_info


async def enrich_company(session, url: str, query: str) -> dict:
    """Legacy-compatible wrapper. Prefer calling scraper functions directly."""
    html = await fetch_page(url, session) if session else None
    info = await extract_page_info(html, url)
    return {
        "url": url,
        "name": info["name"],
        "size": "Mid",
        "industry": query,
        "hiring_signals": "Yes" if info["has_careers"] else "No",
        "contacts": info["emails"],
    }
