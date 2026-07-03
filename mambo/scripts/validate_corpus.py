"""Corpus integrity validation against the AI4I Track 1 "AI-ready data" expectations.

Checks the live Knowledge Store for: allow-list discipline (every source host is a
registered official domain), source uniqueness, chunk counts by ministry, embedding
completeness, OCR coverage, missing critical fields, orphan chunks, and embedding
dimension consistency. Read-only. No network calls.

Usage:
  uv run python scripts/validate_corpus.py                 # print summary
  uv run python scripts/validate_corpus.py --out report.json   # also write JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.db import get_conn  # noqa: E402

REGISTRY = json.loads(
    (Path(__file__).resolve().parent.parent / "registry" / "ministries.json").read_text())


def allowed_hosts() -> set[str]:
    return {h for m in REGISTRY["ministries"] for h in m.get("domains", [])}


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def main() -> int:
    allowed = allowed_hosts()
    report: dict = {"ministries": {}, "checks": {}, "violations": {}}

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM ministries WHERE enabled=true;")
        enabled = {r["id"] for r in cur.fetchall()}

        cur.execute("SELECT source_url, title, raw_path, ocr_used, ministry_id FROM documents;")
        docs = cur.fetchall()

        cur.execute("SELECT count(*) AS n FROM chunks;")
        total_chunks = cur.fetchone()["n"]
        cur.execute("SELECT count(*) AS n FROM chunks WHERE embedding IS NULL;")
        null_embed = cur.fetchone()["n"]
        cur.execute("SELECT count(*) AS n FROM chunks WHERE dim IS NULL AND embedding IS NOT NULL;")
        dim_missing = cur.fetchone()["n"]

        cur.execute("SELECT ministry_id, count(*) AS n FROM chunks GROUP BY ministry_id;")
        chunks_by_min = {r["ministry_id"]: r["n"] for r in cur.fetchall()}

        cur.execute("""SELECT count(*) AS n FROM chunks c
                       LEFT JOIN documents d ON d.id = c.document_id
                       WHERE d.id IS NULL;""")
        orphan_chunks = cur.fetchone()["n"]

    # --- checks ---
    hosts = [host_of(d["source_url"]) for d in docs]
    off_allow = sorted({d["source_url"] for d in docs
                        if host_of(d["source_url"]) not in allowed})
    dup_urls = [u for u, c in Counter(d["source_url"] for d in docs).items() if c > 1]
    missing_title = sum(1 for d in docs if not (d["title"] or "").strip())
    missing_raw = sum(1 for d in docs if not (d["raw_path"] or "").strip())
    ocr_docs = sum(1 for d in docs if d["ocr_used"])
    docs_off_ministry = [d["source_url"] for d in docs if d["ministry_id"] not in enabled]

    report["summary"] = {
        "enabled_ministries": sorted(enabled),
        "documents": len(docs),
        "chunks": total_chunks,
        "ocr_documents": ocr_docs,
    }
    report["checks"] = {
        "allow_list_discipline": {"ok": len(off_allow) == 0, "off_allow_count": len(off_allow)},
        "source_url_uniqueness": {"ok": len(dup_urls) == 0, "duplicate_count": len(dup_urls)},
        "no_orphan_chunks": {"ok": orphan_chunks == 0, "orphan_count": orphan_chunks},
        "embedding_completeness": {
            "total": total_chunks, "null": null_embed,
            "complete_pct": round(100 * (total_chunks - null_embed) / total_chunks, 2)
                            if total_chunks else None},
        "dim_labelled": {"ok": dim_missing == 0, "unlabelled_embedded": dim_missing},
        "titles_present": {"ok": missing_title == 0, "missing": missing_title},
        "raw_paths_present": {"ok": missing_raw == 0, "missing": missing_raw},
        "documents_map_to_enabled_ministries": {"ok": len(docs_off_ministry) == 0,
                                                "off_count": len(docs_off_ministry)},
    }
    report["chunks_by_ministry"] = chunks_by_min
    report["violations"] = {
        "off_allow_list_sample": off_allow[:20],
        "duplicate_urls_sample": dup_urls[:20],
    }

    # --- print ---
    print(f"Ministries enabled : {len(enabled)}  -> {', '.join(sorted(enabled))}")
    print(f"Documents          : {len(docs)}   (OCR used on {ocr_docs})")
    print(f"Chunks             : {total_chunks}   (embedded: "
          f"{report['checks']['embedding_completeness']['complete_pct']}%, NULL={null_embed})")
    print(f"Chunks by ministry : {chunks_by_min}")
    print("\nChecks:")
    for name, res in report["checks"].items():
        flag = "OK " if res.get("ok", True) else "FAIL"
        print(f"  [{flag}] {name}: { {k:v for k,v in res.items() if k!='ok'} }")
    if off_allow:
        print(f"\nOff-allow-list source URLs (first {len(report['violations']['off_allow_list_sample'])}):")
        for u in report["violations"]["off_allow_list_sample"]:
            print(f"    {u}")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, default=str))
        print(f"\nReport written to {args.out}")

    failed = [n for n, r in report["checks"].items() if r.get("ok") is False]
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="path to write JSON report")
    args = ap.parse_args()
    raise SystemExit(main())
