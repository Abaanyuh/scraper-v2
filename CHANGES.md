# 🔧 Changes Made — v2.0 Rewrite

## Summary

The original project was a **scaffold** — all scraping functions returned hardcoded dummy data (`example-company-N.com`, fake event names). It would compile but produced no real results. v2.0 is a complete rewrite into a **working web scraper** with real DuckDuckGo search, page fetching, metadata extraction, and polished CLI.

---

## 1. Added `core/__init__.py`

**Problem:** Python could not import from `core/` as a package because `__init__.py` was missing.

**Fix:** Created package marker with explicit `__all__` exports.

---

## 2. Added `core/scraper.py` (new file)

**Problem:** No actual web-scraping logic existed anywhere. Discovery, events, and enrichment all generated fake data.

**Fix:** New module with:
- `search_ddg()` — queries DuckDuckGo's HTML (non‑JS) endpoint via `aiohttp`, parses results with `BeautifulSoup`
- `fetch_page()` — downloads a page and returns its HTML
- `extract_page_info()` — pulls company name (from `<title>`), meta description, meta keywords, emails, and hiring‑signal detection
- `RateLimiter` — ensures ≥2 second delay between requests to avoid IP bans
- `_extract_ddg_url()` — unwraps DuckDuckGo's redirect links to get real destination URLs

---

## 3. Rewrote `core/discovery.py`

**Before:** Returned hardcoded `example-company-N.com` entries with fake data.

**After:**
- Searches DuckDuckGo for the user's keyword
- Visits each result page in sequence (with rate limiting)
- Extracts real metadata via `extract_page_info()`
- Checks SQLite cache to skip duplicate URLs
- Includes a `_guess_size()` heuristic based on keywords in the description
- Falls back gracefully when pages can't be fetched

---

## 4. Rewrote `core/events.py`

**Before:** Returned 5 hardcoded `{city} Tech Mixer` entries with `asyncio.sleep(1)`.

**After:**
- Searches DuckDuckGo for `"{city} networking events business mixer"`
- Parses real result titles, URLs, and snippets
- Scans for 16 refreshment keywords (buffet, happy hour, open bar, canapés, etc.)
- Attempts date extraction from snippet text with regex
- Rate‑limited to 2.5s between requests

---

## 5. Refactored `core/enrichment.py`

**Before:** Returned hardcoded `size = "Mid"`, `industry = query`, fake contacts.

**After:** Now a thin wrapper around `core/scraper.py` functions. All real enrichment logic moved to `extract_page_info()`.

---

## 6. Improved `core/contacts.py`

**Before:** Capped at 4 results, had a smaller generic‑alias list.

**After:**
- Configurable `max_emails` parameter (default 5)
- Expanded generic‑alias set (12 entries including webmaster, postmaster, abuse, marketing, press, media)
- Cleaner docstring

---

## 7. Enhanced `core/excel_exporter.py`

**Before:** Basic export with no column‑width auto‑sizing.

**After:**
- Column auto‑width with min/max bounds via `_auto_width()`
- Header alignment (centered, wrap‑text)
- Proper Overview sheet with timestamp
- Contacts sheet for email extraction results
- Graceful CSV fallback if `openpyxl` is unavailable
- All paths resolved relative to project root (not `os.getcwd()`)
- `subprocess.run` instead of `subprocess.call` (modern API)

---

## 8. Rewrote `main.py`

**Before:**
- Used `import importlib.util` which can fail
- Silently skipped dependency install when not in venv (printed message, then crashed on import)
- Clunky fallback `Console`/`Prompt` classes
- Called `console.clear()` (jarring full‑screen clear)
- Pointless `setup_directories()` call (dirs already exist in repo)

**After:**
- `from importlib import util as importlib_util` — reliable import
- Dependency installer **exits with clear instructions** if not in a venv (instead of crashing silently)
- Uses project‑root resolution via `Path(__file__).resolve().parent`
- Cleaner menu with `rich` formatting (no full‑screen clear)
- Working **Stats** view (reads actual SQLite cache size + row count)
- Shorter, more readable code (180 lines vs 130 lines of scaffold)
- Added `#!/usr/bin/env python3` shebang

---

## 9. Updated `requirements.txt`

Added minimum version pins (`>=`) for all dependencies.

---

## 10. Added `.gitignore`

Prevents committing:
- Virtual environments
- Python cache files (`__pycache__/`, `*.pyc`)
- Scraped data (`data/*.db`, `exports/*.xlsx`, `exports/*.csv`)
- OS junk (`.DS_Store`, `Thumbs.db`)
- IDE configs (`.vscode/`, `.idea/`)

---

## 11. Added `run.sh` (macOS/Linux launcher)

Automatically creates a `venv`, installs dependencies, and launches `main.py`. No‑brainer for non‑technical users.

---

## 12. Added `run_windows.bat` (Windows launcher)

Same as above for Windows. Double‑click to run.

---

## 13. Added `pyproject.toml`

Standard Python packaging metadata. Enables `pip install -e .` for developers.

---

## 14. Rewrote `README.md`

Complete rewrite with:
- Feature table
- Quick start for all OSes
- Menu walkthrough
- Project structure diagram
- Requirements section

---

## How to Verify the Fixes

```bash
cd "scraper v2"
./run.sh
# Or: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python main.py
```

Then test:
1. **Option 1** → type `fintech startups` → 5 results → Excel should open
2. **Option 2** → type `Dubai` → 5 results → check refreshment signals
3. **Option 3** → shows cache stats
4. **Option 4** → clears cache

---

## What Was Not Changed

- The overall menu structure (5 options, same numbering)
- The Excel export format (same columns, similar styling)
- The SQLite cache approach (same `data/` directory, same schema)
- The email extraction regex (improved filter list only)
