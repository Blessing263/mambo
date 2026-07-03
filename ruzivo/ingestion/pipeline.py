"""Ingestion orchestrator + CLI.

Ties the stages together:  fetch → extract (PDF/OCR or HTML) → chunk → embed → load.
Saves the raw original for provenance. Incremental via content hashing.

Examples:
    uv run python -m ingestion.pipeline --url https://www.ictministry.gov.zw/
    uv run python -m ingestion.pipeline --ministry ict --max-docs 6 --max-pages 30
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .allowlist import ministry_for_url
from .chunk import chunk_pages
from .discover import discover
from .extract import extract_html, extract_pdf
from .fetch import FetchBlocked, fetch
from .store import already_ingested, sha256, store_document

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "raw_docs"
REGISTRY = json.loads((REPO_ROOT / "registry" / "ministries.json").read_text())

# CPU embedding of an 8B model costs ~16s/chunk, so cap chunks per document to keep
# ingestion time predictable. Early sections of policy docs carry the key content.
# Override per run, e.g. RUZIVO_MAX_CHUNKS_PER_DOC=30 for a fast demo pass.
MAX_CHUNKS_PER_DOC = int(os.environ.get("RUZIVO_MAX_CHUNKS_PER_DOC", "150"))

# Set RUZIVO_NO_EMBED=true to gather documents WITHOUT embedding (fast CPU harvest).
# Embeddings are then applied later in bulk — e.g. on a RunPod GPU.
NO_EMBED = os.environ.get("RUZIVO_NO_EMBED", "").lower() in ("1", "true", "yes")


def _save_raw(ministry_id: str, content: bytes, content_hash: str, ext: str) -> str:
    out_dir = RAW_DIR / ministry_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{content_hash[:16]}.{ext}"
    path.write_bytes(content)
    return str(path.relative_to(REPO_ROOT))


def ingest_content(
    final_url: str,
    content: bytes,
    content_type: str,
    *,
    ministry_id: str | None = None,
) -> tuple[str, str, int]:
    """Post-fetch ingestion: dedupe → extract (PDF/OCR or HTML) → chunk → embed → load.

    Independent of HOW the bytes were obtained (HTTP client or headless browser),
    so every fetch path shares one trustworthy pipeline. status ∈
    {'ingested', 'skipped', 'empty', 'blocked'}.
    """
    ministry_id = ministry_id or ministry_for_url(final_url)
    if not ministry_id:
        return ("blocked", f"{final_url} (no ministry)", 0)

    content_hash = sha256(content)
    if already_ingested(final_url, content_hash):
        return ("skipped", final_url, 0)

    is_pdf = "pdf" in content_type or final_url.lower().endswith(".pdf")
    if is_pdf:
        extracted = extract_pdf(content)
        doc_type, ext = "pdf", "pdf"
    else:
        extracted = extract_html(content, final_url)
        doc_type, ext = "html", "html"

    chunks = chunk_pages(extracted["pages"])
    if not chunks:
        return ("empty", final_url, 0)
    if len(chunks) > MAX_CHUNKS_PER_DOC:
        chunks = chunks[:MAX_CHUNKS_PER_DOC]

    raw_path = _save_raw(ministry_id, content, content_hash, ext)
    title = extracted["title"] or final_url
    _doc_id, n = store_document(
        source_url=final_url,
        ministry_id=ministry_id,
        title=title,
        doc_type=doc_type,
        content_hash=content_hash,
        page_count=extracted["page_count"],
        ocr_used=extracted["ocr_used"],
        chunks=chunks,
        raw_path=raw_path,
    )
    return ("ingested", final_url, n)


def ingest_url(
    url: str,
    *,
    ministry_id: str | None = None,
    prefetched: bytes | None = None,
    prefetched_content_type: str = "text/html",
) -> tuple[str, str, int]:
    """Ingest a single URL via the polite HTTP client (or pre-fetched bytes)."""
    if prefetched is not None:
        return ingest_content(
            url, prefetched, prefetched_content_type, ministry_id=ministry_id
        )
    try:
        content, content_type, final_url = fetch(url)
    except FetchBlocked as exc:
        return ("blocked", f"{url} ({exc})", 0)
    return ingest_content(final_url, content, content_type, ministry_id=ministry_id)


def _registry_entry(ministry_id: str) -> dict:
    for m in REGISTRY["ministries"]:
        if m["id"] == ministry_id:
            return m
    raise SystemExit(f"Unknown ministry id: {ministry_id}")


def ingest_ministry(ministry_id: str, *, max_docs: int = 8, max_pages: int = 40) -> None:
    entry = _registry_entry(ministry_id)
    seeds = entry.get("seed_urls", []) + entry.get("doc_pages", [])
    print(f"[{ministry_id}] discovering from {len(seeds)} seed(s)…")
    found = discover(seeds, max_pages=max_pages, max_docs=max_docs)
    print(f"[{ministry_id}] found {len(found['pdf_urls'])} PDF(s), "
          f"{len(found['html_pages'])} HTML page(s). Ingesting…")

    ingested = skipped = empty = blocked = 0
    # Ingest a few content pages (already fetched during discovery) + the PDFs.
    for url, content in found["html_pages"][:max_pages]:
        status, where, n = ingest_url(url, ministry_id=ministry_id, prefetched=content)
        print(f"  [{status}] {where} ({n} chunks)")
        ingested += status == "ingested"; skipped += status == "skipped"
        empty += status == "empty"; blocked += status == "blocked"
    for url in found["pdf_urls"]:
        status, where, n = ingest_url(url, ministry_id=ministry_id)
        print(f"  [{status}] {where} ({n} chunks)")
        ingested += status == "ingested"; skipped += status == "skipped"
        empty += status == "empty"; blocked += status == "blocked"

    print(f"[{ministry_id}] done — ingested {ingested}, skipped {skipped}, "
          f"empty {empty}, blocked {blocked}.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Ruzivo ingestion pipeline")
    ap.add_argument("--url", help="ingest a single allow-listed URL")
    ap.add_argument("--ministry", help="ministry id to crawl + ingest (e.g. ict)")
    ap.add_argument("--max-docs", type=int, default=8)
    ap.add_argument("--max-pages", type=int, default=40)
    args = ap.parse_args()

    if args.url:
        print(ingest_url(args.url))
    elif args.ministry:
        ingest_ministry(args.ministry, max_docs=args.max_docs, max_pages=args.max_pages)
    else:
        ap.error("provide --url or --ministry")


if __name__ == "__main__":
    main()
