"""Staging manifests — the save-first / sort-later layer.

Layout:
    staging/<source_id>/raw/<hash16>.<ext>     exact bytes as acquired
    staging/<source_id>/manifest.jsonl         one JSON record per file

Everything acquired (web crawl or local import) lands here BEFORE any DB write,
so gathering needs no database and curation can run continuously: records carry
a status lifecycle (pending → needs_review/approved/rejected → ingested), a
category, free-form tags/flags, and a full change history. Automated passes
(scripts/curate.py scan) only ever touch records whose last decision was made
by "auto" — a human decision is final until a human changes it.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = REPO_ROOT / "staging"

STATUSES = ("pending", "needs_review", "approved", "rejected", "ingested")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def source_dir(source_id: str) -> Path:
    return STAGING_DIR / source_id


def raw_dir(source_id: str) -> Path:
    return source_dir(source_id) / "raw"


def manifest_path(source_id: str) -> Path:
    return source_dir(source_id) / "manifest.jsonl"


def raw_path(record: dict) -> Path:
    return raw_dir(record["source_id"]) / f"{record['hash'][:16]}.{record['ext']}"


def iter_sources() -> Iterator[str]:
    if not STAGING_DIR.exists():
        return
    for p in sorted(STAGING_DIR.iterdir()):
        if p.is_dir() and (p / "manifest.jsonl").exists():
            yield p.name


def new_record(
    *,
    source_id: str,
    content: bytes,
    ext: str,
    filename: str,
    content_type: str = "",
    url: str | None = None,
    provenance: str = "web",
    local_origin: str | None = None,
    title: str | None = None,
) -> dict:
    """A fresh manifest record. `kind`/`page_count`/`category` are filled by
    the curate scan pass; `cite_url` is the URL answers should cite (defaults
    to `url` for web acquisitions, must be set manually for local files)."""
    return {
        "hash": sha256(content),
        "source_id": source_id,
        "filename": filename,
        "ext": ext,
        "size": len(content),
        "content_type": content_type,
        "url": url,
        "cite_url": url,
        "provenance": provenance,
        "local_origin": local_origin,
        "fetched_at": now_iso(),
        "title": title,
        "kind": None,
        "page_count": None,
        "text_chars": None,
        "category": None,
        "tags": [],
        "flags": [],
        "status": "pending",
        "reject_reason": None,
        "notes": None,
        "history": [],
        "extra": {},
    }


def load_manifest(source_id: str) -> dict[str, dict]:
    """hash → record. Later lines win, so appends are safe crash-wise."""
    path = manifest_path(source_id)
    records: dict[str, dict] = {}
    if not path.exists():
        return records
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        records[rec["hash"]] = rec
    return records


def save_manifest(source_id: str, records: dict[str, dict]) -> None:
    path = manifest_path(source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w") as f:
        for rec in records.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def append_record(source_id: str, record: dict) -> None:
    path = manifest_path(source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def last_decider(record: dict) -> str | None:
    """Who made the most recent status/category decision: 'auto' or 'manual'."""
    for event in reversed(record.get("history", [])):
        if "status" in event.get("set", {}) or "category" in event.get("set", {}):
            return event.get("by")
    return None


def apply_change(record: dict, *, by: str, why: str | None = None, **fields) -> bool:
    """Set fields on a record, appending a history event. Returns True if
    anything actually changed. `by` is 'auto' or 'manual'."""
    changed = {k: v for k, v in fields.items() if record.get(k) != v}
    if not changed:
        return False
    record.update(changed)
    record["history"].append(
        {"at": now_iso(), "by": by, "why": why, "set": changed}
    )
    return True


def save_bytes(source_id: str, content: bytes, ext: str) -> Path:
    """Write raw bytes to the staging raw/ dir, keyed by content hash."""
    out = raw_dir(source_id)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{sha256(content)[:16]}.{ext}"
    if not path.exists():
        path.write_bytes(content)
    return path


# --- Run ledger ------------------------------------------------------------------
# Every acquisition run is recorded in staging/runs.jsonl: parameters, deadline
# (the run's contracted end time), heartbeats, and final status. This is what
# `scripts/curate.py status` reads to monitor background runs.

RUNS_PATH = STAGING_DIR / "runs.jsonl"


def load_runs() -> dict[str, dict]:
    runs: dict[str, dict] = {}
    if not RUNS_PATH.exists():
        return runs
    for line in RUNS_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            rec = json.loads(line)
            runs[rec["run_id"]] = rec
    return runs


def update_run(run: dict) -> None:
    """Upsert one run record (also serves as the heartbeat)."""
    run["heartbeat_at"] = now_iso()
    runs = load_runs()
    runs[run["run_id"]] = run
    RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = RUNS_PATH.with_suffix(".jsonl.tmp")
    with tmp.open("w") as f:
        for rec in runs.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(RUNS_PATH)


# --- Per-source lock -------------------------------------------------------------
# Prevents two concurrent runs from hammering the same source (wasted bandwidth,
# duplicate work). Stale locks (dead PID) are recovered automatically.

def acquire_lock(source_id: str) -> Path:
    lock = source_dir(source_id) / ".lock"
    if lock.exists():
        try:
            info = json.loads(lock.read_text())
            os.kill(int(info["pid"]), 0)  # raises if the process is gone
            raise SystemExit(
                f"[{source_id}] already being acquired by pid {info['pid']} "
                f"(since {info.get('started_at')}). Remove {lock} if that is wrong."
            )
        except (ProcessLookupError, ValueError, KeyError, json.JSONDecodeError):
            pass  # stale or corrupt lock — recover it
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "started_at": now_iso()}))
    return lock


def release_lock(source_id: str) -> None:
    (source_dir(source_id) / ".lock").unlink(missing_ok=True)
