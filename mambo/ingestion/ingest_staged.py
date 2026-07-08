"""Ingest approved staging records into the Knowledge Store (needs the DB).

Stage 3 of the save-first workflow: only records curated to status=approved
flow into ingest_content(), so the store never sees unsorted noise. Run with
RUZIVO_NO_EMBED=true, then bulk-embed later (ingestion.embed_bulk on GPU).

Citations: web acquisitions cite their fetched URL. Local files must have a
curated `cite_url` (the official page for that document); without one they are
skipped unless --allow-uncited, which falls back to a non-clickable
local://<source>/<filename> marker — honest, but weaker provenance.

    RUZIVO_NO_EMBED=true uv run python -m ingestion.ingest_staged
    RUZIVO_NO_EMBED=true uv run python -m ingestion.ingest_staged --source education
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.pipeline import ingest_content  # noqa: E402
from ingestion.staging import (  # noqa: E402
    apply_change, iter_sources, load_manifest, raw_path, save_manifest,
)


def _content_type(record: dict) -> str:
    if record.get("content_type"):
        return record["content_type"]
    guess, _ = mimetypes.guess_type(f"x.{record['ext']}")
    return guess or "application/octet-stream"


def _cite_url(record: dict, allow_uncited: bool) -> str | None:
    url = record.get("cite_url") or record.get("url")
    if url:
        return url
    if allow_uncited:
        return f"local://{record['source_id']}/{record['filename']}"
    return None


def ingest_source(source_id: str, *, limit: int, allow_uncited: bool) -> dict:
    records = load_manifest(source_id)
    counts = {"ingested": 0, "skipped": 0, "empty": 0, "blocked": 0,
              "uncited": 0, "error": 0, "chunks": 0}
    done = 0
    for rec in records.values():
        if rec["status"] != "approved":
            continue
        if limit and done >= limit:
            break
        url = _cite_url(rec, allow_uncited)
        if url is None:
            counts["uncited"] += 1
            print(f"  [no-cite-url] {rec['hash'][:8]} {rec['filename'][:60]} "
                  "— set one with: scripts/curate.py set <hash> --cite-url …")
            continue
        done += 1
        try:
            content = raw_path(rec).read_bytes()
            status, detail, n_chunks = ingest_content(
                url, content, _content_type(rec), ministry_id=source_id,
            )
        except Exception as exc:  # noqa: BLE001
            counts["error"] += 1
            print(f"  [error] {rec['filename'][:60]}: {exc}")
            continue
        counts[status] = counts.get(status, 0) + 1
        counts["chunks"] += n_chunks
        print(f"  [{status}] {rec['filename'][:60]} ({n_chunks} chunks)")
        if status in ("ingested", "skipped"):
            apply_change(rec, by="auto", why=f"ingest_staged: {status}",
                         status="ingested")
    save_manifest(source_id, records)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", help="one source id (default: all staged)")
    ap.add_argument("--limit", type=int, default=0, help="max docs per source")
    ap.add_argument("--allow-uncited", action="store_true",
                    help="ingest local files lacking cite_url under local://")
    args = ap.parse_args()

    sources = [args.source] if args.source else list(iter_sources())
    if not sources:
        raise SystemExit("staging/ is empty — nothing to ingest")

    totals: dict[str, int] = {}
    for source_id in sources:
        print(f"[{source_id}] ingesting approved records…")
        counts = ingest_source(source_id, limit=args.limit,
                               allow_uncited=args.allow_uncited)
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + v
    print("\nTotals: " + "  ".join(f"{k}={v}" for k, v in totals.items() if v))
    if totals.get("chunks"):
        print("Next: bulk-embed on GPU — see ingestion/embed_bulk.py header.")


if __name__ == "__main__":
    main()
