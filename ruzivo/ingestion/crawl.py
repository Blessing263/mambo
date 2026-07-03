"""Deep, sitemap-aware crawler — gather a source's real content pages + PDFs.

Combines the sitemap (complete page list) with a bounded breadth-first crawl from
the seeds, using smart_fetch (browser fallback) so Cloudflare/JS pages are reached.
Ingests every content page (not just landing pages + PDFs) — which is where the
"how do I…" citizen guidance actually lives.

    RUZIVO_NO_EMBED=true uv run python -m ingestion.crawl zimra home_affairs \
        --max-pages 150 --max-depth 2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.allowlist import is_allowed  # noqa: E402
from ingestion.pipeline import ingest_content  # noqa: E402
from ingestion.sitemap import sitemap_urls  # noqa: E402
from ingestion.smartfetch import smart_fetch  # noqa: E402

REGISTRY = json.loads(
    (Path(__file__).resolve().parent.parent / "registry" / "ministries.json").read_text()
)

# Skip obvious non-content URLs (assets, feeds, logins, pagination noise).
_SKIP = re.compile(
    r"\.(css|js|png|jpe?g|gif|svg|ico|woff2?|ttf|eot|mp4|zip)(\?|$)"
    r"|/(login|signin|register|cart|search|tag/|feed|rss|wp-json|administrator)\b",
    re.IGNORECASE,
)


def _entry(ministry_id: str) -> dict:
    for m in REGISTRY["ministries"]:
        if m["id"] == ministry_id:
            return m
    raise SystemExit(f"unknown source: {ministry_id}")


def crawl_source(ministry_id: str, *, max_pages: int = 150, max_depth: int = 2,
                 delay: float = 0.8) -> None:
    entry = _entry(ministry_id)
    seeds = entry.get("seed_urls", []) + entry.get("doc_pages", [])
    sm: list[str] = []
    for domain in entry["domains"]:
        sm += sitemap_urls(domain, max_urls=max_pages * 3)
    print(f"[{ministry_id}] {len(seeds)} seeds + {len(sm)} sitemap URLs")

    queue: deque[tuple[str, int]] = deque((u, 0) for u in seeds + sm)
    seen: set[str] = set()
    counts: Counter = Counter()
    visited = 0

    while queue and visited < max_pages:
        url, depth = queue.popleft()
        url = urldefrag(url)[0]
        if url in seen or not is_allowed(url) or _SKIP.search(url):
            continue
        seen.add(url)
        visited += 1
        try:
            content, ctype, final = smart_fetch(url)
        except Exception:
            counts["fetch-fail"] += 1
            continue

        status, _w, nchunks = ingest_content(final, content, ctype, ministry_id=ministry_id)
        counts[status] += 1
        if status == "ingested" and counts["ingested"] % 15 == 0:
            print(f"  [{ministry_id}] {counts['ingested']} ingested / {visited} visited")

        if depth < max_depth and "html" in ctype:
            try:
                soup = BeautifulSoup(content, "lxml")
                for a in soup.find_all("a", href=True):
                    link = urldefrag(urljoin(final, a["href"]))[0]
                    if is_allowed(link) and link not in seen and not _SKIP.search(link):
                        queue.append((link, depth + 1))
            except Exception:
                pass
        time.sleep(delay)

    print(f"[{ministry_id}] done: {dict(counts)} ({visited} visited)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Deep sitemap-aware crawler")
    ap.add_argument("sources", nargs="+", help="ministry/source ids")
    ap.add_argument("--max-pages", type=int, default=150)
    ap.add_argument("--max-depth", type=int, default=2)
    args = ap.parse_args()
    for sid in args.sources:
        crawl_source(sid, max_pages=args.max_pages, max_depth=args.max_depth)


if __name__ == "__main__":
    main()
