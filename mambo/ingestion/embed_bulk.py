"""Bulk embedder — fill every NULL embedding via the priority provider.

With OpenAI as the priority embedding provider (shared/embeddings.py) this
needs no GPU at all: it batches chunk texts to the API and writes vectors
back. Idempotent and restart-safe: it only ever selects rows whose embedding
is NULL, so it can be killed and resumed at any point.

Covers both embedding tables: `chunks` (the corpus) and
`official_response_chunks` (reviewed answers).

Usage:
    uv run python -m ingestion.embed_bulk                 # everything pending
    uv run python -m ingestion.embed_bulk --limit 30      # smoke test

Ollama fallback (no OpenAI key, or EMBED_PROVIDER=ollama) — e.g. RunPod GPU:
    export OLLAMA_BASE_URL=https://<POD_ID>-11434.proxy.runpod.net
    export EMBED_PROVIDER=ollama EMBED_MODEL=qwen3-embedding:8b EMBED_DIM=4096
    uv run python -m ingestion.embed_bulk
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.config import settings  # noqa: E402
from shared.db import get_conn  # noqa: E402
from shared.embeddings import embed_batch  # noqa: E402

BATCH_SIZE = int(os.environ.get("RUZIVO_EMBED_BATCH", "32"))

TABLES = ("chunks", "official_response_chunks")


def pending_count(cur, table: str) -> int:
    cur.execute(f"SELECT count(*) FROM {table} WHERE embedding IS NULL;")  # noqa: S608
    return cur.fetchone()["count"]


def fill_batch(cur, table: str, batch_size: int, skip: list[str]) -> list[dict]:
    cur.execute(
        f"SELECT id, text FROM {table} "  # noqa: S608
        "WHERE embedding IS NULL AND NOT (id::text = ANY(%s)) LIMIT %s;",
        (skip or ["00000000-0000-0000-0000-000000000000"], batch_size),
    )
    return cur.fetchall()


def write_back(cur, table: str, updates: list[tuple[str, np.ndarray]]) -> None:
    for cid, vec in updates:
        cur.execute(
            f"UPDATE {table} SET embedding=%s, dim=%s WHERE id=%s;",  # noqa: S608
            (vec, int(vec.size), cid),
        )


def embed_table(conn, cur, table: str, *, limit: int) -> int:
    remaining = pending_count(cur, table)
    if not remaining:
        return 0
    print(f"[{table}] {remaining} row(s) to embed.")
    total = 0
    failed: list[str] = []  # permanently failed ids — skip so the loop terminates
    while True:
        rows = fill_batch(cur, table, BATCH_SIZE, failed)
        if not rows:
            break
        texts = [r["text"] for r in rows]
        ids = [str(r["id"]) for r in rows]
        try:
            vecs: list[np.ndarray | None] = [
                np.asarray(v, dtype=np.float32) for v in embed_batch(texts)
            ]
        except Exception:
            # Retry one-at-a-time so one oversized chunk doesn't block progress.
            vecs = []
            for t in texts:
                try:
                    vecs.append(np.asarray(embed_batch([t])[0], dtype=np.float32))
                except Exception as exc:  # noqa: BLE001
                    print(f"  [failed] chunk skipped: {exc}")
                    vecs.append(None)
        updates = []
        for cid, v in zip(ids, vecs):
            if v is None:
                failed.append(cid)
            else:
                updates.append((cid, v))
        write_back(cur, table, updates)
        conn.commit()
        total += len(updates)
        remaining -= len(rows)
        if limit and total >= limit:
            break
        if total and total % 200 < BATCH_SIZE:
            print(f"  …{total} embedded, ~{remaining} left")
    if failed:
        print(f"[{table}] {len(failed)} row(s) could not be embedded "
              "(left NULL — rerun after investigating).")
    return total


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int,
                    default=int(os.environ.get("RUZIVO_EMBED_LIMIT", "0")),
                    help="max rows per table (0 = unlimited)")
    args = ap.parse_args()

    provider = "openai" if (settings.embed_provider != "ollama"
                            and settings.openai_api_key) else "ollama"
    model = (settings.openai_embed_model if provider == "openai"
             else settings.embed_model)
    print(f"Embedder: {provider}:{model} dim={settings.embed_dim} batch={BATCH_SIZE}")

    t0 = perf_counter()
    total = 0
    with get_conn() as conn, conn.cursor() as cur:
        for table in TABLES:
            cur.execute("SELECT to_regclass(%s) AS t;", (table,))
            if cur.fetchone()["t"] is None:
                print(f"[{table}] not present in this DB — skipped.")
                continue
            total += embed_table(conn, cur, table, limit=args.limit)
    dt = perf_counter() - t0
    rate = total / dt if dt else 0.0
    print(f"Done. {total} row(s) in {dt:.1f}s ({rate:.2f} rows/s).")


if __name__ == "__main__":
    main()
