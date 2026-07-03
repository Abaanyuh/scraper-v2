"""
Export discovery results to formatted Excel (.xlsx) or CSV fallback.
"""

import csv
import os
import platform
import subprocess
from datetime import datetime

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    USE_OPENPYXL = True
except ImportError:
    USE_OPENPYXL = False


def export_and_open(
    companies: list[dict] | None = None,
    events: list[dict] | None = None,
) -> str:
    """
    Write results to ``exports/`` and attempt to open the file.

    Returns the output file path (or an empty string on failure).
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    os.makedirs(out_dir, exist_ok=True)

    if USE_OPENPYXL:
        return _export_xlsx(out_dir, ts, companies, events)
    return _export_csv(out_dir, ts, companies, events)


# ---------------------------------------------------------------------------
# XLSX export
# ---------------------------------------------------------------------------

HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _style_header(ws):
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN


def _auto_width(ws, min_w=10, max_w=50):
    for col_idx, col_cells in enumerate(ws.columns, 1):
        longest = min_w
        for cell in col_cells:
            if cell.value:
                longest = max(longest, min(len(str(cell.value)), max_w))
        ws.column_dimensions[get_column_letter(col_idx)].width = longest + 2


def _export_xlsx(out_dir: str, ts: str, companies, events) -> str:
    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet

    # -- Overview --
    ws = wb.create_sheet("Overview")
    ws.append(["Metric", "Value"])
    ws.append(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    ws.append(["Companies found", len(companies) if companies else 0])
    ws.append(["Events found", len(events) if events else 0])
    _style_header(ws)
    _auto_width(ws)

    # -- Companies --
    if companies:
        ws = wb.create_sheet("Companies")
        ws.append(["Company Name", "URL", "Industry", "Size", "Hiring?", "Description"])
        for c in companies:
            ws.append([
                c.get("name", ""),
                c.get("url", ""),
                c.get("industry", ""),
                c.get("size", ""),
                c.get("hiring_signals", ""),
                c.get("description", ""),
            ])
        _style_header(ws)
        _auto_width(ws)

        # -- Contacts --
        ws = wb.create_sheet("Contacts")
        ws.append(["Company", "Email"])
        for c in companies:
            for email in c.get("contacts", []):
                ws.append([c.get("name", ""), email])
        _style_header(ws)
        _auto_width(ws)

    # -- Events --
    if events:
        ws = wb.create_sheet("Networking Events")
        ws.append(["Event Name", "Venue / City", "Date", "URL", "Refreshment Signal"])
        for ev in events:
            ws.append([
                ev.get("name", ""),
                ev.get("venue", ""),
                ev.get("date", ""),
                ev.get("url", ""),
                ev.get("refreshment_signal", ""),
            ])
        _style_header(ws)
        _auto_width(ws)

    filepath = os.path.join(out_dir, f"Discovery_Run_{ts}.xlsx")
    wb.save(filepath)
    print(f"\n  ✅ Saved: {filepath}")
    _open_file(filepath)
    return filepath


# ---------------------------------------------------------------------------
# CSV fallback
# ---------------------------------------------------------------------------

def _export_csv(out_dir: str, ts: str, companies, events) -> str:
    paths: list[str] = []

    if companies:
        p = os.path.join(out_dir, f"Discovery_Run_{ts}_companies.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Company Name", "URL", "Industry", "Size", "Hiring?", "Description"])
            for c in companies:
                w.writerow([
                    c.get("name", ""), c.get("url", ""), c.get("industry", ""),
                    c.get("size", ""), c.get("hiring_signals", ""), c.get("description", ""),
                ])
        paths.append(p)

    if events:
        p = os.path.join(out_dir, f"Discovery_Run_{ts}_events.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Event Name", "Venue / City", "Date", "URL", "Refreshment Signal"])
            for ev in events:
                w.writerow([
                    ev.get("name", ""), ev.get("venue", ""), ev.get("date", ""),
                    ev.get("url", ""), ev.get("refreshment_signal", ""),
                ])
        paths.append(p)

    for p in paths:
        print(f"  ✅ Saved CSV: {p}")
    return "\n".join(paths)


# ---------------------------------------------------------------------------
# OS file opener
# ---------------------------------------------------------------------------

def _open_file(filepath: str):
    try:
        sys = platform.system()
        if sys == "Windows":
            os.startfile(filepath)
        elif sys == "Darwin":
            subprocess.run(["open", filepath], check=False)
        else:
            subprocess.run(["xdg-open", filepath], check=False)
    except Exception as exc:
        print(f"  ⚠️ Could not auto-open: {exc}")
