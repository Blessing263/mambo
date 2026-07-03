"""Browser-based harvesting for JS-rendered / CDN-challenged official sites.

Uses a real headless Chromium (ingestion.browser) to render seed pages, collect
allow-listed links and document URLs, and ingest them through the shared pipeline
(ingestion.pipeline.ingest_content). Citations still point to the official URLs.

    uv run python -m ingestion.harvest --url https://zimtreasury.co.zw/      # probe render
    uv run python -m ingestion.harvest --ministry finance                    # harvest + ingest
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urldefrag

from .allowlist import is_allowed
from .browser import browser_fetch, browser_get_bytes
from .pipeline import ingest_content

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = json.loads((REPO_ROOT / "registry" / "ministries.json").read_text())


def _entry(ministry_id: str) -> dict:
    for m in REGISTRY["ministries"]:
        if m["id"] == ministry_id:
            return m
    raise SystemExit(f"Unknown ministry id: {ministry_id}")


def harvest_ministry(ministry_id: str, *, max_pdfs: int = 10, max_pages: int = 5) -> None:
    entry = _entry(ministry_id)
    seeds = entry.get("seed_urls", []) + entry.get("doc_pages", [])
    prime = (entry.get("seed_urls") or [None])[0]
    print(f"[{ministry_id}] browser-harvesting from {len(seeds)} seed(s)…")

    pdf_urls: list[str] = []
    content_pages: list[tuple[str, str]] = []

    for seed in seeds:
        if seed.lower().endswith(".pdf"):
            if seed not in pdf_urls:
                pdf_urls.append(seed)
            continue
        try:
            res = browser_fetch(seed)
        except Exception as exc:  # noqa: BLE001
            print(f"  [render-failed] {seed} ({exc})")
            continue
        print(f"  [rendered] {seed} → {len(res['links'])} links "
              f"(challenge cleared: {res['challenged']})")
        content_pages.append((res["url"], res["html"]))
        for link in res["links"]:
            link = urldefrag(link)[0]
            if is_allowed(link) and link.lower().endswith(".pdf") and link not in pdf_urls:
                pdf_urls.append(link)

    print(f"[{ministry_id}] {len(pdf_urls)} PDF(s), {len(content_pages)} page(s). Ingesting…")
    for url in pdf_urls[:max_pdfs]:
        try:
            body, ctype = browser_get_bytes(url, prime_url=prime)
            print("   ", ingest_content(url, body, ctype or "application/pdf",
                                        ministry_id=ministry_id))
        except Exception as exc:  # noqa: BLE001
            print(f"  [pdf-failed] {url} ({exc})")
    for url, html in content_pages[:max_pages]:
        try:
            print("   ", ingest_content(url, html.encode("utf-8"), "text/html",
                                        ministry_id=ministry_id))
        except Exception as exc:  # noqa: BLE001
            print(f"  [page-failed] {url} ({exc})")
    print(f"[{ministry_id}] browser-harvest done.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Browser-based harvester")
    ap.add_argument("--url", help="probe: render one URL and report links/PDFs (no ingest)")
    ap.add_argument("--ministry", help="harvest + ingest a ministry via the browser")
    args = ap.parse_args()

    if args.url:
        res = browser_fetch(args.url)
        pdfs = [l for l in res["links"] if l.lower().endswith(".pdf")]
        print(json.dumps({
            "final_url": res["url"],
            "title": res["title"],
            "challenge_cleared": res["challenged"],
            "n_links": len(res["links"]),
            "pdf_links": pdfs[:25],
        }, indent=2))
    elif args.ministry:
        harvest_ministry(args.ministry)
    else:
        ap.error("provide --url or --ministry")


if __name__ == "__main__":
    main()
