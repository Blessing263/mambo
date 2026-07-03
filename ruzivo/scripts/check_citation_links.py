"""Check that cited source URLs resolve (HTTP). Broken links undermine trust —
every citation should point at a live official page (or be archived).

Checks a SAMPLE by default (official sites can be slow / rate-limited). Raise the
limit for a fuller sweep.

Usage:
  uv run python scripts/check_citation_links.py --limit 30
  uv run python scripts/check_citation_links.py --all --out links.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from shared.db import get_conn  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30, help="sample size (0/--all = all)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT source_url FROM documents ORDER BY source_url;")
        urls = [r["source_url"] for r in cur.fetchall()]

    if not args.all and args.limit:
        urls = urls[: args.limit]

    print(f"Checking {len(urls)} source URLs (timeout {args.timeout}s)…")
    results = []
    broken = []
    with httpx.Client(timeout=args.timeout, follow_redirects=True,
                      headers={"User-Agent": "Ruzivo-Citation-Check/1.0"}) as client:
        for u in urls:
            ok = False
            status = None
            err = None
            try:
                r = client.head(u)
                # some servers reject HEAD; fall back to GET
                if r.status_code >= 400:
                    r = client.get(u)
                status = r.status_code
                ok = r.status_code < 400
            except Exception as e:  # noqa: BLE001
                err = type(e).__name__
            results.append({"url": u, "status": status, "ok": ok, "error": err})
            if not ok:
                broken.append(results[-1])
            flag = "ok" if ok else "BROKEN"
            print(f"  [{flag}] {status or err}  {u}")

    print(f"\n{len(results) - len(broken)}/{len(results)} resolved; {len(broken)} broken.")
    summary = {
        "checked": len(results),
        "resolved": len(results) - len(broken),
        "broken": broken,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2))
        print(f"Written to {args.out}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
