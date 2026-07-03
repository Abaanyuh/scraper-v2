#!/usr/bin/env python3
"""
Lead & Event Discovery Platform v2.0
====================================
A CLI web scraper that searches the web for companies and networking events,
enriches results with real metadata, and exports formatted Excel spreadsheets.

Usage:
    python main.py          → interactive menu
    python main.py --help   → see all options
"""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
import sys
from importlib import util as importlib_util
from pathlib import Path

# ---------------------------------------------------------------------------
# 0. Ensure we run from the project root (so data/ and exports/ resolve)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)

# ---------------------------------------------------------------------------
# 1. Zero-setup dependency installer
# ---------------------------------------------------------------------------
REQUIRED: dict[str, str] = {
    "rich": "rich",
    "openpyxl": "openpyxl",
    "aiohttp": "aiohttp",
    "bs4": "beautifulsoup4",
    "tqdm": "tqdm",
}


def _in_venv() -> bool:
    return (
        (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        or "VIRTUAL_ENV" in os.environ
        or "CONDA_PREFIX" in os.environ
    )


def _install_missing():
    missing = [pip_name for mod, pip_name in REQUIRED.items() if importlib_util.find_spec(mod) is None]
    if not missing:
        return

    if not _in_venv():
        print("=" * 60)
        print("  ⚠️  Missing packages:", ", ".join(missing))
        print("  This Python environment appears to be system-managed.")
        print("  Please create a virtual environment first:")
        print()
        print("    python3 -m venv venv")
        print("    source venv/bin/activate       # macOS / Linux")
        print("    venv\\Scripts\\activate          # Windows")
        print("    pip install -r requirements.txt")
        print()
        print("  OR use the launcher script:")
        print("    ./run.sh                       # macOS / Linux")
        print("    run_windows.bat                # Windows")
        print("=" * 60)
        sys.exit(1)

    print("  ⏳ Installing dependencies …")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", *missing],
        )
        print("  ✅ Dependencies installed.\n")
    except subprocess.CalledProcessError:
        print("  ❌ pip install failed. Check your internet connection.")
        sys.exit(1)


_install_missing()

# ---------------------------------------------------------------------------
# 2. Imports (safe now)
# ---------------------------------------------------------------------------
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

from core.discovery import run_company_discovery, clear_cache
from core.events import scrape_networking_events
from core.excel_exporter import export_and_open

console = Console()


# ---------------------------------------------------------------------------
# 3. Menu
# ---------------------------------------------------------------------------

def _show_banner():
    console.print(
        Panel.fit(
            "[bold cyan]LEAD & EVENT DISCOVERY PLATFORM  v2.0[/]\n"
            "[dim]Real-time web scraping  ·  Excel export  ·  Contact extraction[/]",
            border_style="cyan",
        )
    )


async def main_loop():
    _show_banner()

    while True:
        console.print()
        console.print("[1] [bold]Discover Companies[/] by keyword")
        console.print("[2] [bold]Find Networking Events[/] by city (with refreshment signals)")
        console.print("[3] [bold]View Stats[/] (cache size)")
        console.print("[4] [bold]Clear Cache[/]")
        console.print("[5] [bold]Exit[/]")
        console.print()

        choice = Prompt.ask("Choose", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            query = Prompt.ask("  Industry / keyword")
            n = IntPrompt.ask("  Max results", default=10)
            console.print(f"\n  🔍 Discovering companies for [bold]'{query}'[/] …\n")
            companies = await run_company_discovery(query, n)
            if companies:
                console.print(f"\n  ✅ {len(companies)} companies found.")
                export_and_open(companies=companies)
            else:
                console.print("  ⚠️ No results. Try a broader keyword.")

        elif choice == "2":
            city = Prompt.ask("  City")
            n = IntPrompt.ask("  Max results", default=10)
            console.print(f"\n  🎉 Searching events in [bold]{city}[/] …\n")
            events = await scrape_networking_events(city, n)
            if events:
                console.print(f"\n  ✅ {len(events)} events found.")
                export_and_open(events=events)
            else:
                console.print("  ⚠️ No events found. Try a different city.")

        elif choice == "3":
            db = PROJECT_ROOT / "data" / "discovered.db"
            size = os.path.getsize(db) if db.exists() else 0
            console.print(f"\n  📊 Cache DB: {db}")
            console.print(f"  📏 Size: {size:,} bytes")
            if db.exists():
                import sqlite3
                conn = sqlite3.connect(str(db))
                count = conn.execute("SELECT COUNT(*) FROM scraped").fetchone()[0]
                conn.close()
                console.print(f"  🔗 Unique URLs cached: {count}")

        elif choice == "4":
            clear_cache()
            console.print("  ✅ Cache cleared.")

        elif choice == "5":
            console.print("\n  👋 Goodbye!\n")
            break

        Prompt.ask("\n  Press Enter to continue")


# ---------------------------------------------------------------------------
# 4. Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n  👋 Interrupted. Goodbye!")
        sys.exit(0)
