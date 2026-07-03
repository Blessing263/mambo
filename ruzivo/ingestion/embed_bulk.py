"""Bulk embedder — point at a GPU Ollama and fill every NULL embedding chunk.

Designed for RunPod or any remote GPU instance serving Ollama at <OLLAMA_BASE_URL>.
Runs idempotently: restart-safe, skips already-embedded rows.

Usage (local CPU verify):
    uv run python -m ingestion.embed_bulk --limit 30

Usage (RunPod GPU):
    # HTTP ports are exposed via a proxy URL — there is NO public IP.
    # Format: https://<POD_ID>-11434.proxy.runpod.net  (pod env: OLLAMA_HOST=0.0.0.0)
    export OLLAMA_BASE_URL=https://<POD_ID>-11434.proxy.runpod.net
    export EMBED_MODEL=qwen3-embedding:8b EMBED_DIM=4096 RUZIVO_EMBED_BATCH=64
    uv run python -m ingestion.embed_bulk

Keep batches small enough that each /api/embed call finishes within the proxy's
~100s Cloudflare timeout (batch 64 on an A100 ≈ 6s — well within).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.db import get_conn  # noqa: E402
from shared.embeddings import embed_batch  # noqa: E402

BATCH_SIZE = int(os.environ.get("RUZIVO_EMBED_BATCH", "32"))
FETCH_LIMIT = int(os.environ.get("RUZIVO_EMBED_LIMIT", "0"))  # 0 = unlimited


def pending_count(cur) -> int:
    cur.execute("SELECT count(*) FROM chunks WHERE embedding IS NULL;")
    return cur.fetchone()["count"]


def fill_batch(cur, batch_size: int) -> list[dict]:
    cur.execute(
        "SELECT id, text FROM chunks WHERE embedding IS NULL LIMIT %s;",
        (batch_size,),
    )
    return cur.fetchall()


def write_back(cur, updates: list[tuple[str, np.ndarray]], dim: int) -> None:
    for cid, vec in updates:
        cur.execute("UPDATE chunks SET embedding=%s, dim=%s WHERE id=%s;", (vec, dim, cid))


def main() -> None:
    model = os.environ.get("EMBED_MODEL", "nomic-embed-text")
    dim = int(os.environ.get("EMBED_DIM", "768"))
    print(f"Embedder: {model} @ "
          f"{os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11435')} "
          f"batch={BATCH_SIZE} dim={dim}")
    total = 0
    t0 = perf_counter()
    with get_conn() as conn, conn.cursor() as cur:
        remaining = pending_count(cur)
        print(f"{remaining} chunks to embed.")
        while True:
            rows = fill_batch(cur, BATCH_SIZE)
            if not rows:
                break
            texts = [r["text"] for r in rows]
            ids = [r["id"] for r in rows]
            try:
                vecs = [np.asarray(v, dtype=np.float32) for v in embed_batch(texts)]
            except Exception:
                # Retry one-at-a-time so one oversized chunk doesn't block progress.
                vecs = []
                for t in texts:
                    try:
                        vecs.append(np.asarray(embed_batch([t])[0], dtype=np.float32))
                    except Exception:
                        vecs.append(np.zeros(0, dtype=np.float32))
            updates = [(cid, v if v.size > 0 else None) for cid, v in zip(ids, vecs)]
            write_back(cur, updates, dim)
            conn.commit()
            total += len(updates)
            remaining -= len(updates)
            if FETCH_LIMIT and total >= FETCH_LIMIT:
                break
            if total % 200 == 0:
                print(f"  …{total} embedded, {remaining} left")
    dt = perf_counter() - t0
    print(f"Done. {total} chunks in {dt:.1f}s ({total/dt:.2f} chunks/s).")


if __name__ == "__main__":
    main()
