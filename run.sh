#!/usr/bin/env bash
# -------------------------------------------------------------------------
# Launcher for macOS / Linux — creates venv, installs deps, runs the scraper
# -------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "🔧 Creating virtual environment …"
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo ""
python main.py
