"""Curate — continuous sorting of the staging area (NO database needed).

Runs any number of times as new data arrives. The scan pass classifies files
(pdf-text / pdf-scanned / docx / html / unsupported), then applies the rules in
staging/curation_rules.json — a data file you edit as the corpus evolves.
Automated passes never override a manual decision (tracked via record history).

    uv run python scripts/curate.py scan                     # classify + apply rules
    uv run python scripts/curate.py stats                    # where things stand
    uv run python scripts/curate.py list --status pending    # review queue
    uv run python scripts/curate.py show 1f56d81d            # text preview
    uv run python scripts/curate.py set 1f56d81d --set-status approved --set-category syllabus
    uv run python scripts/curate.py set --source education --category hr-admin \\
        --set-status rejected --reason pii        # bulk by filter
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.staging import (  # noqa: E402
    STAGING_DIR, STATUSES, apply_change, iter_sources, last_decider,
    load_manifest, raw_path, save_manifest,
)

RULES_PATH = STAGING_DIR / "curation_rules.json"

# Starter rules, written on first scan if no rules file exists. `match` is a
# case-insensitive regex tested against the filename (on: name) or the first
# ~2000 chars of extracted text (on: text). First matching rule wins.
DEFAULT_RULES = {
    "note": "Edit freely — curate.py scan re-applies on every run. First match "
            "wins. Rules only ever touch records whose last decision was "
            "automatic; manual decisions stick.",
    "rules": [
        {"match": r"promotion list|interview (list|schedule)|shortlist|vacancy|advert|recruitment",
         "on": "name", "category": "hr-admin", "status": "rejected", "reason": "hr/pii"},
        {"match": r"hbc (ventures|plus ?one)|ventures g7|plusone",
         "on": "name", "category": "commercial-textbook", "status": "rejected",
         "reason": "copyright"},
        {"match": r"scheme[- ]?cum|term \d.*scheme|scheme.*term \d|lesson plan",
         "on": "name", "category": "teaching-material", "status": "needs_review",
         "reason": "third-party teaching material"},
        {"match": r"\bact\b.*\d{4}|\[ ?act \d+-\d+ ?\]|statutory instrument",
         "on": "name", "category": "legislation", "status": "needs_review",
         "reason": "legislation — consider citing the Veritas copy"},
        {"match": r"syllabus", "on": "name", "category": "syllabus",
         "status": "needs_review"},
        {"match": r"circular|pay dates", "on": "name", "category": "circular",
         "status": "needs_review"},
        {"match": r"^\d{4}q\d{2}|question paper|marking scheme",
         "on": "name", "category": "exam-paper", "status": "needs_review",
         "reason": "ZIMSEC exam material — check reproduction policy"},
        {"match": r"form(s)?\b|\bcdef\b", "on": "name", "category": "form",
         "status": "needs_review"},
    ],
}

UNSUPPORTED_EXTS = {"rtf", "odt", "doc", "xls", "xlsx", "csv", "pptx"}
ARCHIVE_EXTS = {"zip", "7z"}

# Below this many extracted characters a document is probably nav-only/junk.
MIN_TEXT_CHARS = 250


def _load_rules() -> list[dict]:
    if not RULES_PATH.exists():
        RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        RULES_PATH.write_text(json.dumps(DEFAULT_RULES, indent=2) + "\n")
        print(f"[rules] wrote starter rules → {RULES_PATH}")
    return json.loads(RULES_PATH.read_text())["rules"]


def _classify(record: dict) -> dict:
    """kind / page_count / text_chars / title for one staged file.
    Fast pass: no OCR (scanned PDFs are OCR'd at ingest time instead)."""
    path = raw_path(record)
    ext = record["ext"]
    out: dict = {}
    if ext in ARCHIVE_EXTS:
        return {"kind": "archive"}
    if ext in UNSUPPORTED_EXTS:
        return {"kind": f"unsupported-{ext}"}
    try:
        if ext == "pdf":
            import fitz  # noqa: PLC0415
            doc = fitz.open(str(path))
            sample = "".join(doc[i].get_text() for i in range(min(3, doc.page_count)))
            total = sum(len(doc[i].get_text()) for i in range(doc.page_count))
            out = {
                "kind": "pdf-text" if len(sample.strip()) > 200 else "pdf-scanned",
                "page_count": doc.page_count,
                "text_chars": total,
                "title": record["title"] or (doc.metadata or {}).get("title") or None,
            }
            doc.close()
        elif ext == "docx":
            from ingestion.extract import extract_docx  # noqa: PLC0415
            ex = extract_docx(path.read_bytes())
            text = " ".join(t for _, t in ex["pages"])
            out = {"kind": "docx", "text_chars": len(text),
                   "title": record["title"] or ex.get("title")}
        elif ext in ("html", "htm", "txt"):
            from ingestion.extract import extract_html  # noqa: PLC0415
            ex = extract_html(path.read_bytes(), record.get("url") or "")
            text = " ".join(t for _, t in ex["pages"])
            out = {"kind": "html", "text_chars": len(text),
                   "title": record["title"] or ex.get("title")}
        else:
            out = {"kind": f"unknown-{ext}"}
    except Exception as exc:  # noqa: BLE001
        out = {"kind": "error", "notes": f"classify failed: {exc}"}
    return out


def _preview_text(record: dict, chars: int) -> str:
    path = raw_path(record)
    ext = record["ext"]
    try:
        if ext == "pdf":
            import fitz  # noqa: PLC0415
            doc = fitz.open(str(path))
            text = "".join(doc[i].get_text() for i in range(min(5, doc.page_count)))
            doc.close()
            if not text.strip() and record.get("kind") == "pdf-scanned":
                return "(scanned PDF — text will be OCR'd at ingest time)"
            return text[:chars]
        from ingestion.extract import extract_docx, extract_html  # noqa: PLC0415
        if ext == "docx":
            ex = extract_docx(path.read_bytes())
        else:
            ex = extract_html(path.read_bytes(), record.get("url") or "")
        return " ".join(t for _, t in ex["pages"])[:chars]
    except Exception as exc:  # noqa: BLE001
        return f"(preview failed: {exc})"


def _apply_rules(record: dict, rules: list[dict]) -> bool:
    """First matching rule sets category/status — but only over auto decisions."""
    if last_decider(record) == "manual":
        return False
    text_sample: str | None = None
    for rule in rules:
        if rule.get("on", "name") == "name":
            hay = record["filename"]
        else:
            if text_sample is None:  # lazy: only extract when a text rule exists
                text_sample = _preview_text(record, 2000)
            hay = text_sample
        if re.search(rule["match"], hay or "", re.IGNORECASE):
            return apply_change(
                record, by="auto", why=f"rule: {rule['match'][:40]}",
                category=rule.get("category", record["category"]),
                status=rule.get("status", record["status"]),
                reject_reason=rule.get("reason", record["reject_reason"]),
            )
    return False


def cmd_scan(args) -> None:
    rules = _load_rules()
    for source_id in _sources(args):
        records = load_manifest(source_id)
        changed = 0
        for rec in records.values():
            if rec["kind"] is None or args.rescan:
                info = _classify(rec)
                notes = info.pop("notes", None)
                if apply_change(rec, by="auto", why="scan classify",
                                **info, **({"notes": notes} if notes else {})):
                    changed += 1
            if last_decider(rec) != "manual":
                # structural flags before content rules
                if rec["kind"] in ("archive",) or (rec["kind"] or "").startswith(
                        ("unsupported", "unknown", "error")):
                    changed += apply_change(
                        rec, by="auto", why=f"format: {rec['kind']}",
                        status="needs_review",
                        flags=sorted({*rec["flags"], "unsupported-format"}))
                elif (rec["text_chars"] is not None
                      and rec["text_chars"] < MIN_TEXT_CHARS
                      and rec["kind"] != "pdf-scanned"):
                    changed += apply_change(
                        rec, by="auto", why="near-empty extraction",
                        status="needs_review",
                        flags=sorted({*rec["flags"], "thin-content"}))
            changed += _apply_rules(rec, rules)
        save_manifest(source_id, records)
        print(f"[{source_id}] scanned {len(records)} record(s), {changed} change(s).")


def _sources(args) -> list[str]:
    if getattr(args, "source", None):
        return [args.source]
    found = list(iter_sources())
    if not found:
        raise SystemExit("staging/ is empty — run ingestion.acquire first")
    return found


def _select(records: dict, args) -> list[dict]:
    out = []
    for rec in records.values():
        if args.status and rec["status"] != args.status:
            continue
        if args.category and rec["category"] != args.category:
            continue
        if args.kind and rec["kind"] != args.kind:
            continue
        if args.flag and args.flag not in rec["flags"]:
            continue
        if args.name and not re.search(args.name, rec["filename"], re.IGNORECASE):
            continue
        if args.hashes and not any(rec["hash"].startswith(h) for h in args.hashes):
            continue
        out.append(rec)
    return out


def cmd_status(args) -> None:
    """Background-run monitoring: live/stale/finished runs + frontier backlogs."""
    from datetime import datetime, timedelta, timezone
    from ingestion.staging import load_runs, source_dir

    runs = sorted(load_runs().values(), key=lambda r: r["started_at"])
    if not runs:
        print("no acquisition runs recorded yet")
    stale_after = datetime.now(timezone.utc) - timedelta(minutes=5)
    for run in runs[-args.last:]:
        status = run["status"]
        if status == "running":
            hb = datetime.fromisoformat(run["heartbeat_at"])
            lock = source_dir(run["source_id"]) / ".lock"
            if hb < stale_after and not lock.exists():
                status = "crashed?"  # stale heartbeat, no live lock
        print(f"  {run['run_id']:<28} {status:<17} pages={run['pages']:<4} "
              f"docs={run['docs']:<4} new={run['staged_new']:<4} "
              f"dups={run['dups']:<3} skip={run['url_skips']:<3} "
              f"hb={run['heartbeat_at']}")
    print()
    for source_id in iter_sources():
        frontier = source_dir(source_id) / "frontier.json"
        if frontier.exists():
            backlog = len(json.loads(frontier.read_text()).get("queue", []))
            print(f"  [{source_id}] frontier backlog: {backlog} URL(s) — "
                  "rerun acquire to resume")


def cmd_stats(args) -> None:
    for source_id in _sources(args):
        records = load_manifest(source_id)
        by_status: dict[str, int] = {}
        by_cat: dict[str, int] = {}
        for rec in records.values():
            by_status[rec["status"]] = by_status.get(rec["status"], 0) + 1
            by_cat[rec["category"] or "(none)"] = by_cat.get(rec["category"] or "(none)", 0) + 1
        print(f"[{source_id}] {len(records)} file(s)")
        print("  status:  " + "  ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
        print("  category:" + "  ".join(f"{k}={v}" for k, v in sorted(by_cat.items())))


def cmd_list(args) -> None:
    for source_id in _sources(args):
        records = load_manifest(source_id)
        rows = _select(records, args)
        if not rows:
            continue
        print(f"[{source_id}] {len(rows)} match(es)")
        for rec in rows:
            cite = "" if rec["cite_url"] or rec["provenance"] == "web" else "  NO-CITE-URL"
            print(f"  {rec['hash'][:8]}  {rec['status']:<12} "
                  f"{(rec['category'] or '-'):<20} {(rec['kind'] or '?'):<12} "
                  f"{rec['filename'][:55]}{cite}")


def cmd_show(args) -> None:
    for source_id in _sources(args):
        records = load_manifest(source_id)
        for rec in records.values():
            if rec["hash"].startswith(args.hash):
                print(json.dumps({k: v for k, v in rec.items() if k != "history"},
                                 indent=2, ensure_ascii=False))
                for event in rec["history"]:
                    print(f"  history: {event['at']} [{event['by']}] "
                          f"{event.get('why') or ''} → {event['set']}")
                print("\n--- preview ---")
                print(_preview_text(rec, args.chars))
                return
    raise SystemExit(f"no staged record matching hash prefix {args.hash!r}")


def cmd_set(args) -> None:
    fields: dict = {}
    if args.set_status:
        fields["status"] = args.set_status
    if args.set_category:
        fields["category"] = args.set_category
    if args.cite_url:
        fields["cite_url"] = args.cite_url
    if args.reason:
        fields["reject_reason"] = args.reason
    if args.notes:
        fields["notes"] = args.notes
    if not fields and not args.tag:
        raise SystemExit("nothing to set — pass --set-status/--set-category/"
                         "--cite-url/--reason/--notes/--tag")
    total = 0
    for source_id in _sources(args):
        records = load_manifest(source_id)
        rows = _select(records, args)
        for rec in rows:
            extra = {}
            if args.tag:
                extra["tags"] = sorted({*rec["tags"], *args.tag})
            if apply_change(rec, by="manual", why=args.why, **fields, **extra):
                total += 1
        if rows:
            save_manifest(source_id, records)
    print(f"updated {total} record(s).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def selectors(p, hashes: bool = True) -> None:
        p.add_argument("--source", help="limit to one source id")
        p.add_argument("--status", choices=STATUSES)
        p.add_argument("--category")
        p.add_argument("--kind")
        p.add_argument("--flag")
        p.add_argument("--name", help="regex on filename")
        if hashes:
            p.add_argument("hashes", nargs="*", help="hash prefix(es)")

    p = sub.add_parser("scan", help="classify new files + apply rules")
    p.add_argument("--source")
    p.add_argument("--rescan", action="store_true", help="re-classify everything")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("stats", help="counts by status/category")
    p.add_argument("--source")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("status", help="acquisition runs: live, stale, finished")
    p.add_argument("--last", type=int, default=15, help="show the last N runs")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("list", help="list records matching filters")
    selectors(p)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="full record + text preview")
    p.add_argument("hash")
    p.add_argument("--source")
    p.add_argument("--chars", type=int, default=1500)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("set", help="manual decision on matching records")
    selectors(p)
    p.add_argument("--set-status", choices=STATUSES)
    p.add_argument("--set-category")
    p.add_argument("--cite-url")
    p.add_argument("--reason")
    p.add_argument("--notes")
    p.add_argument("--tag", action="append")
    p.add_argument("--why", help="recorded in history")
    p.set_defaults(func=cmd_set)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
