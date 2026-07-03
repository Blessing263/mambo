"""Render the Track 3 proposal Markdown to a format-compliant PDF.

Pipeline: pandoc (md -> html) -> HTML wrapper with print CSS -> Playwright (html -> pdf).
Formatting meets the Track 3 ToR: A4, Arial 11pt, 1.15 line spacing, 1-inch margins.

Usage:  uv run python scripts/render_proposal.py
Output: submission/mambo_AI4I_Proposal_Development.pdf
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB = ROOT / "submission"
MD = SUB / "proposal.md"
PANDOC = "/home/blessing/bin/pandoc"

CSS = """
@page { size: A4; margin: 1in; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; }
body { font-family: Arial, "Avenir Next", "Liberation Sans", sans-serif;
       font-size: 11pt; line-height: 1.15; color: #111; margin: 0; }
h1 { font-size: 16pt; margin-top: 1.1em; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
h2 { font-size: 13pt; margin-top: 1em; }
p, li { font-size: 11pt; line-height: 1.15; }
.cover { page-break-after: always; text-align: center; padding-top: 5cm; }
.cover h1 { font-size: 30pt; border: none; margin-bottom: 0.4em; }
.cover p { font-size: 13pt; margin: 0.3em 0; }
strong { font-weight: bold; }
pre { background: #f6f6f6; padding: 8px; border-radius: 4px; white-space: pre-wrap;
      font-size: 9pt; line-height: 1.1; }
code { font-family: "Courier New", monospace; }
hr { border: none; border-top: 1px solid #bbb; margin: 1.4em 0; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; }
th, td { border: 1px solid #ccc; padding: 4px 6px; text-align: left; }
"""

MARGINS = {"top": "1in", "bottom": "1in", "left": "1in", "right": "1in"}


def main() -> int:
    if not MD.exists():
        print("missing", MD, file=sys.stderr); return 1
    fragment = subprocess.check_output(
        [PANDOC, str(MD), "-f", "markdown", "-t", "html5"], text=True)
    doc = (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
           f"<style>{CSS}</style></head><body>{fragment}</body></html>")
    (SUB / "_proposal.html").write_text(doc)

    from playwright.sync_api import sync_playwright
    out = SUB / "mambo_AI4I_Proposal_Development.pdf"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(doc, wait_until="load")
        page.pdf(path=str(out), format="A4", margin=MARGINS, print_background=True)
        browser.close()
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
