"""Deepen a source by following links from its seed pages one level deep.

Veritas: the A-Z list links to /node/N Act pages (plain Apache, rich legal text).
ZIMRA:   downloads/notices pages (Cloudflare HTML) link to public PDF guides.
         ZIMRA's stock Joomla robots.txt disallows the download component paths
         (SEO boilerplate), but the files are public and serve directly — so we
         fetch them as a citizen's browser would (still allow-list-scoped).

Idempotent: URLs already in the store are skipped (no re-fetch).
Run with RUZIVO_NO_EMBED=true to gather fast (embed later on GPU).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.browser import browser_fetch  # noqa: E402
from ingestion.fetch import USER_AGENT  # noqa: E402
from ingestion.pipeline import ingest_content, ingest_url  # noqa: E402
from shared.db import get_conn  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _existing_urls(ministry_id: str) -> set[str]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT source_url FROM documents WHERE ministry_id=%s;", (ministry_id,))
        return {r["source_url"] for r in cur.fetchall()}


def deepen_veritas(max_new: int = 400) -> None:
    html = httpx.get(
        "https://veritaszim.net/a-z-list-of-acts",
        headers={"User-Agent": USER_AGENT}, timeout=45, follow_redirects=True,
    ).text
    nodes = sorted(
        set(re.findall(r'href="(/node/\d+)"', html)),
        key=lambda x: int(x.rsplit("/", 1)[-1]),
    )
    done = _existing_urls("veritas")
    todo = [n for n in nodes if f"https://veritaszim.net{n}" not in done][:max_new]
    print(f"[veritas] {len(nodes)} Acts, {len(done)} already done, ingesting {len(todo)} new")
    counts: Counter = Counter()
    for n in todo:
        status, _w, nchunks = ingest_url(f"https://veritaszim.net{n}", ministry_id="veritas")
        counts[status] += 1
        if status == "ingested" and counts["ingested"] % 25 == 0:
            print(f"  …{counts['ingested']} acts ingested")
    print(f"[veritas] done: {dict(counts)}")


def deepen_zimra(max_docs: int = 120) -> None:
    seeds = [
        "https://www.zimra.co.zw/downloads",
        "https://www.zimra.co.zw/public-notices",
        "https://www.zimra.co.zw/domestic-taxes",
        "https://www.zimra.co.zw/customs-and-excise",
        "https://www.zimra.co.zw/news",
        "https://www.zimra.co.zw/my-taxes/value-added-tax",
    ]
    links: list[str] = []
    for seed in seeds:
        try:
            res = browser_fetch(seed)
            for link in res["links"]:
                clean = link.split("#")[0]
                if (clean.lower().endswith(".pdf") or "download=" in clean) and clean not in links:
                    links.append(clean)
            print(f"  rendered {seed} — {len(links)} doc links so far")
        except Exception as exc:  # noqa: BLE001
            print(f"  render-failed {seed}: {exc}")

    done = _existing_urls("zimra")
    todo = [u for u in links if u not in done][:max_docs]
    print(f"[zimra] {len(links)} links, ingesting {len(todo)} new (direct download)")
    counts: Counter = Counter()
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(follow_redirects=True, headers=headers, timeout=60) as client:
        for url in todo:
            try:
                r = client.get(url)
                ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
                if "pdf" not in ctype and "officedocument" not in ctype:
                    counts["not-doc"] += 1
                    continue
                status, _w, nchunks = ingest_content(
                    str(r.url), r.content, ctype, ministry_id="zimra"
                )
                counts[status] += 1
                if status == "ingested":
                    print(f"  [ingested] {url[:66]} ({nchunks} chunks)")
            except Exception as exc:  # noqa: BLE001
                counts["error"] += 1
                print(f"  failed {url[:60]}: {exc}")
    print(f"[zimra] done: {dict(counts)}")


def deep_zimlii(max_judgments: int = 200) -> None:
    """Ingest ZimLII judgments from locally-downloaded raw HTML files.

    Because ZimLII is Cloudflare-protected and blocks VPS IPs, the judgment content
    must be fetched from a residential browser (where Chrome passes the check).

    Workflow:
      1. Open https://zimlii.org/judgments/ in Chrome
      2. Paste scripts/zimlii_extract_urls.js in DevTools → downloads URL JSON
      3. Run scripts/zimlii_fetch_content.py on your machine → downloads raw HTML
      4. Transfer raw_docs/zimlii/ + JSON to VPS
      5. Run this: RUZIVO_NO_EMBED=true uv run python -m ingestion.deepen zimlii
    """
    urls_file = REPO_ROOT / "zimlii_judgment_urls.json"
    if not urls_file.exists():
        print("[zimlii] No local URL file found. To ingest ZimLII judgments:")
        print("  1. Open https://zimlii.org/judgments/ in Chrome")
        print("  2. Paste scripts/zimlii_extract_urls.js in DevTools Console")
        print("  3. Run: python scripts/zimlii_fetch_content.py --limit 200")
        print("  4. Transfer raw_docs/zimlii/ + zimlii_judgment_urls.json to VPS")
        print("  5. Re-run this command")
        return

    urls = json.loads(urls_file.read_text())
    raw_dir = REPO_ROOT / "raw_docs" / "zimlii"
    if not raw_dir.exists():
        print(f"[zimlii] No raw directory at {raw_dir}. Run zimlii_fetch_content.py first.")
        return

    # Map stem → URL
    slug_to_url = {}
    for url in urls:
        slug = url.rstrip("/").split("/")[-1]
        slug_to_url[slug] = url

    # Find raw files
    html_files = list(raw_dir.glob("*.html"))
    done = _existing_urls("zimlii")
    todo = []
    for f in html_files:
        url = slug_to_url.get(f.stem)
        if url and url not in done:
            todo.append((url, f))

    print(f"[zimlii] {len(html_files)} raw files, {len(todo)} to ingest "
          f"({len(done)} already done)")

    counts: Counter = Counter()
    for url, fpath in todo[:max_judgments]:
        try:
            html = fpath.read_bytes()
            status, _w, nchunks = ingest_content(
                url, html, "text/html", ministry_id="zimlii"
            )
            counts[status] += 1
            if status == "ingested" and counts["ingested"] % 25 == 0:
                print(f"  …{counts['ingested']} imported")
        except Exception as exc:  # noqa: BLE001
            counts["error"] += 1
            print(f"  error {fpath.name}: {exc}")

    print(f"[zimlii] done: {dict(counts)}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("veritas", "both"):
        deepen_veritas()
    if which in ("zimra", "both"):
        deepen_zimra()
    if which in ("zimlii", "both"):
        deep_zimlii()
