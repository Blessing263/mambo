"""Acquire — save-only harvesting into the staging area (NO database needed).

Stage 1 of the save-first workflow: gather everything allow-listed into
staging/<source_id>/ with a manifest, sort it with scripts/curate.py, then
ingest only approved records via ingestion.ingest_staged (on the DB box).

Built for long unattended background runs:
- Contract: --budget-minutes is the run's hard end time. It stops cleanly at
  the deadline and saves its crawl frontier to staging/<source>/frontier.json.
- Resume: a saved frontier is picked up by the next run, continuing the crawl
  where it stopped instead of starting over.
- Recovery: a per-source lockfile stops concurrent duplicate runs; locks held
  by dead processes are reclaimed automatically.
- No waste: document URLs staged within --refresh-days are not re-downloaded
  (content-hash dedupe already prevents duplicate *storage*; this saves the
  bandwidth as well). HTML pages are cheap and are re-walked for discovery.
- Monitoring: every run heartbeats into staging/runs.jsonl —
  `uv run python scripts/curate.py status` shows live/finished runs.

Examples:
    uv run python -m ingestion.acquire --all --budget-minutes 120
    uv run python -m ingestion.acquire --ministry zimra --max-pages 60 --max-docs 100
    uv run python -m ingestion.acquire --ministry nssa --browser        # CF/JS sites
    uv run python -m ingestion.acquire --import-dir ~/ndei/syllabus --source-id education
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin

# Acquisition never needs the DB — resolve the allow-list from the registry
# JSON directly (must be set before ingestion.allowlist builds its cache).
os.environ.setdefault("RUZIVO_ALLOWLIST", "file")

from bs4 import BeautifulSoup  # noqa: E402

from .allowlist import is_allowed  # noqa: E402
from .fetch import FetchBlocked, fetch  # noqa: E402
from .staging import (  # noqa: E402
    acquire_lock, load_manifest, new_record, now_iso, release_lock, save_bytes,
    save_manifest, source_dir, update_run,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = json.loads((REPO_ROOT / "registry" / "ministries.json").read_text())

# Local files worth staging. Unsupported-for-extraction formats (rtf, archives)
# are still saved — "keep everything, decide later" — curate flags them.
IMPORT_EXTS = {
    "pdf", "docx", "doc", "html", "htm", "txt", "rtf", "odt",
    "xlsx", "xls", "csv", "pptx", "zip", "7z",
}

DOC_EXTS = (".pdf", ".docx", ".doc", ".xlsx")

HEARTBEAT_EVERY = 10  # fetches between ledger heartbeats / manifest saves


def _entry(ministry_id: str) -> dict:
    for m in REGISTRY["ministries"]:
        if m["id"] == ministry_id:
            return m
    raise SystemExit(f"Unknown ministry id: {ministry_id}")


def _clean(url: str) -> str:
    return urldefrag(url)[0]


def _looks_like_doc(url: str) -> bool:
    return url.lower().endswith(DOC_EXTS)


def _ext_for(content_type: str, url: str) -> str:
    lower = url.lower()
    if "pdf" in content_type or lower.endswith(".pdf"):
        return "pdf"
    if "wordprocessingml.document" in content_type or lower.endswith(".docx"):
        return "docx"
    return "html"


def _extract_links(content: bytes, base_url: str) -> list[str]:
    soup = BeautifulSoup(content, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        link = _clean(urljoin(base_url, a["href"]))
        if link.startswith("http"):
            links.append(link)
    return links


def _stage(records: dict, source_id: str, *, url: str, content: bytes,
           content_type: str, title: str | None = None) -> str:
    """Save bytes + manifest record. Returns 'new' | 'dup'."""
    rec = new_record(
        source_id=source_id,
        content=content,
        ext=_ext_for(content_type, url),
        filename=url.rsplit("/", 1)[-1] or url,
        content_type=content_type,
        url=url,
        provenance="web",
        title=title,
    )
    if rec["hash"] in records:
        return "dup"
    save_bytes(source_id, content, rec["ext"])
    records[rec["hash"]] = rec
    return "new"


def _recent_urls(records: dict, refresh_days: int) -> set[str]:
    """URLs staged within the refresh window — not worth re-downloading."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=refresh_days)) \
        .isoformat(timespec="seconds")
    return {r["url"] for r in records.values()
            if r.get("url") and r["fetched_at"] >= cutoff}


def _frontier_path(source_id: str) -> Path:
    return source_dir(source_id) / "frontier.json"


def _load_frontier(source_id: str, seeds: list[str]) -> deque[str]:
    path = _frontier_path(source_id)
    if path.exists():
        saved = json.loads(path.read_text())
        queue = deque(saved.get("queue", []))
        if queue:
            print(f"[{source_id}] resuming saved frontier "
                  f"({len(queue)} URL(s), saved {saved.get('saved_at')})")
            return queue
    return deque(_clean(u) for u in seeds)


def _save_frontier(source_id: str, queue: deque[str]) -> None:
    path = _frontier_path(source_id)
    if queue:
        path.write_text(json.dumps(
            {"queue": list(queue), "saved_at": now_iso()}, ensure_ascii=False))
    else:
        path.unlink(missing_ok=True)


def acquire_ministry(ministry_id: str, *, max_pages: int, max_docs: int,
                     use_browser: bool, deadline: float | None,
                     refresh_days: int) -> None:
    entry = _entry(ministry_id)
    seeds = entry.get("seed_urls", []) + entry.get("doc_pages", [])
    acquire_lock(ministry_id)
    records = load_manifest(ministry_id)
    run = {
        "run_id": f"{time.strftime('%Y%m%dT%H%M%S')}-{ministry_id}",
        "source_id": ministry_id,
        "mode": "browser" if use_browser else "http",
        "started_at": now_iso(),
        "deadline_at": (time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(deadline))
                        if deadline else None),
        "params": {"max_pages": max_pages, "max_docs": max_docs,
                   "refresh_days": refresh_days},
        "pages": 0, "docs": 0, "staged_new": 0, "dups": 0, "url_skips": 0,
        "status": "running", "ended_at": None,
    }
    update_run(run)
    before = len(records)
    print(f"[{ministry_id}] acquiring from {len(seeds)} seed(s) ({run['mode']})…")
    try:
        if use_browser:
            _crawl_browser(ministry_id, seeds, records, run,
                           max_docs=max_docs, deadline=deadline,
                           refresh_days=refresh_days)
        else:
            _crawl_http(ministry_id, seeds, records, run,
                        max_pages=max_pages, max_docs=max_docs,
                        deadline=deadline, refresh_days=refresh_days)
        if run["status"] == "running":
            run["status"] = "completed"
    except BaseException:
        run["status"] = "error"
        raise
    finally:
        run["ended_at"] = now_iso()
        save_manifest(ministry_id, records)
        update_run(run)
        release_lock(ministry_id)
        print(f"[{ministry_id}] {run['status']}: +{len(records) - before} new "
              f"(pages={run['pages']} docs={run['docs']} dups={run['dups']} "
              f"skipped-recent={run['url_skips']}; {len(records)} total).")


def _crawl_http(source_id: str, seeds: list[str], records: dict, run: dict, *,
                max_pages: int, max_docs: int, deadline: float | None,
                refresh_days: int) -> None:
    recent = _recent_urls(records, refresh_days)
    queue = _load_frontier(source_id, seeds)
    visited: set[str] = set()
    fetches = 0

    while queue:
        if run["pages"] >= max_pages or run["docs"] >= max_docs:
            run["status"] = "limit_reached"
            break
        if deadline and time.time() >= deadline:
            run["status"] = "deadline_reached"
            break
        url = _clean(queue.popleft())
        if url in visited or not is_allowed(url):
            continue
        visited.add(url)
        if _looks_like_doc(url) and url in recent:
            run["url_skips"] += 1  # already staged recently — save the bandwidth
            continue
        try:
            content, content_type, final_url = fetch(url)
        except (FetchBlocked, Exception):  # noqa: BLE001
            continue
        fetches += 1
        final_url = _clean(final_url)

        if "html" in content_type:
            run["pages"] += 1
            status = _stage(records, source_id, url=final_url, content=content,
                            content_type=content_type)
            run["staged_new" if status == "new" else "dups"] += 1
            for link in _extract_links(content, final_url):
                if link not in visited and is_allowed(link):
                    queue.append(link)
        else:
            run["docs"] += 1
            status = _stage(records, source_id, url=final_url, content=content,
                            content_type=content_type)
            run["staged_new" if status == "new" else "dups"] += 1

        if fetches % HEARTBEAT_EVERY == 0:
            # Crash-recovery checkpoint: manifest + frontier + heartbeat, so a
            # hard kill (OOM, reboot) loses at most HEARTBEAT_EVERY fetches.
            save_manifest(source_id, records)
            _save_frontier(source_id, queue)
            update_run(run)

    _save_frontier(source_id, queue if run["status"] in
                   ("deadline_reached", "limit_reached") else deque())


def _crawl_browser(source_id: str, seeds: list[str], records: dict, run: dict, *,
                   max_docs: int, deadline: float | None,
                   refresh_days: int) -> None:
    """Headless-browser variant for CDN-challenged / JS-rendered sites
    (mirrors ingestion.harvest but saves instead of ingesting)."""
    from .browser import browser_fetch, browser_get_bytes  # lazy: needs Playwright

    recent = _recent_urls(records, refresh_days)
    doc_urls: list[str] = []
    for seed in seeds:
        if deadline and time.time() >= deadline:
            run["status"] = "deadline_reached"
            break
        if seed.lower().endswith(".pdf"):
            if seed not in doc_urls:
                doc_urls.append(seed)
            continue
        try:
            res = browser_fetch(seed)
        except Exception as exc:  # noqa: BLE001
            print(f"  [render-failed] {seed} ({exc})")
            continue
        print(f"  [rendered] {seed} → {len(res['links'])} links "
              f"(challenge cleared: {res['challenged']})")
        run["pages"] += 1
        status = _stage(records, source_id, url=res["url"],
                        content=res["html"].encode(), content_type="text/html")
        run["staged_new" if status == "new" else "dups"] += 1
        for link in res["links"]:
            link = _clean(link)
            if is_allowed(link) and _looks_like_doc(link) and link not in doc_urls:
                doc_urls.append(link)
        update_run(run)

    for url in doc_urls[:max_docs]:
        if deadline and time.time() >= deadline:
            run["status"] = "deadline_reached"
            break
        if url in recent:
            run["url_skips"] += 1
            continue
        try:
            content, content_type = browser_get_bytes(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  [download-failed] {url} ({exc})")
            continue
        run["docs"] += 1
        status = _stage(records, source_id, url=url, content=content,
                        content_type=content_type)
        run["staged_new" if status == "new" else "dups"] += 1
        if run["docs"] % HEARTBEAT_EVERY == 0:
            save_manifest(source_id, records)
            update_run(run)


def import_dir(directory: Path, source_id: str) -> None:
    """Stage every interesting file under a local directory tree."""
    _entry(source_id)  # validate against the registry
    records = load_manifest(source_id)
    before = len(records)
    new = dup = skipped = 0
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lstrip(".").lower()
        if ext not in IMPORT_EXTS:
            skipped += 1
            continue
        content = path.read_bytes()
        rec = new_record(
            source_id=source_id,
            content=content,
            ext=ext,
            filename=path.name,
            url=None,
            provenance="local",
            local_origin=str(path),
        )
        rec["cite_url"] = None  # must be curated in before ingest
        if rec["hash"] in records:
            dup += 1
            continue
        save_bytes(source_id, content, ext)
        records[rec["hash"]] = rec
        new += 1
    save_manifest(source_id, records)
    print(f"[{source_id}] imported {new} new, {dup} duplicate(s), "
          f"{skipped} skipped (uninteresting ext) from {directory} "
          f"({len(records) - before:+d} → {len(records)} in manifest).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ministry", help="registry source id to crawl")
    ap.add_argument("--all", action="store_true", help="crawl every enabled source")
    ap.add_argument("--browser", action="store_true",
                    help="use headless Chromium (Cloudflare/JS sites)")
    ap.add_argument("--max-pages", type=int, default=40)
    ap.add_argument("--max-docs", type=int, default=60)
    ap.add_argument("--budget-minutes", type=float, default=0,
                    help="hard end time for this invocation (0 = unlimited); "
                         "unfinished crawls save a frontier and resume next run")
    ap.add_argument("--refresh-days", type=int, default=7,
                    help="don't re-download document URLs staged this recently")
    ap.add_argument("--import-dir", type=Path, help="stage a local directory instead")
    ap.add_argument("--source-id", help="source id for --import-dir")
    args = ap.parse_args()

    if args.import_dir:
        if not args.source_id:
            ap.error("--import-dir requires --source-id")
        import_dir(args.import_dir.expanduser().resolve(), args.source_id)
        return

    if args.all:
        ids = [m["id"] for m in REGISTRY["ministries"] if m.get("enabled", True)]
    elif args.ministry:
        ids = [args.ministry]
    else:
        ap.error("one of --ministry, --all, or --import-dir is required")

    deadline = time.time() + args.budget_minutes * 60 if args.budget_minutes else None
    for mid in ids:
        if deadline and time.time() >= deadline:
            print(f"[{mid}] budget exhausted before this source — rerun to continue.")
            continue
        acquire_ministry(mid, max_pages=args.max_pages, max_docs=args.max_docs,
                         use_browser=args.browser, deadline=deadline,
                         refresh_days=args.refresh_days)


if __name__ == "__main__":
    main()
