"""Ingest chunks into the Knowledge Store.

Incremental: documents are keyed by source_url + content_hash. If a document's
content hasn't changed since last ingest, it is skipped. On change, the document
row is updated and its chunks are fully replaced (so stale text never lingers).

Embedding can be deferred — chunks are stored with a NULL embedding column, then
filled in later by ingestion.embed_bulk (RunPod GPU or local CPU).
"""

from __future__ import annotations

import hashlib
import os
from typing import Sequence

import numpy as np

from shared.db import get_conn

EMBED_BATCH_SIZE = 8
NO_EMBED = os.environ.get("RUZIVO_NO_EMBED", "").lower() in ("1", "true", "yes")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def already_ingested(source_url: str, content_hash: str) -> bool:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT content_hash FROM documents WHERE source_url = %s;", (source_url,)
        )
        row = cur.fetchone()
        return bool(row and row["content_hash"] == content_hash)


def _embed_all(texts: list[str]) -> list[np.ndarray]:
    """If NO_EMBED, return placeholder arrays so chunks are stored NULL."""
    if NO_EMBED:
        return [np.zeros(0, dtype=np.float32)] * len(texts)
    from shared.embeddings import embed_batch  # noqa: PLC0415
    vecs: list[np.ndarray] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        for v in embed_batch(batch, is_query=False):
            vecs.append(np.asarray(v, dtype=np.float32))
    return vecs


def store_document(
    *,
    source_url: str,
    ministry_id: str,
    title: str,
    doc_type: str,
    content_hash: str,
    page_count: int | None,
    ocr_used: bool,
    chunks: list[dict],
    raw_path: str | None = None,
) -> tuple[str, int]:
    """Persist a document and its chunks. Returns (document_id, n_chunks).

    Embeddings are stored if available; NULL otherwise (deferred to embed_bulk later).
    """
    vectors = _embed_all([c["text"] for c in chunks])

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents
                (ministry_id, source_url, title, doc_type, content_hash,
                 page_count, ocr_used, raw_path, fetched_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), 'active')
            ON CONFLICT (source_url) DO UPDATE SET
                ministry_id  = EXCLUDED.ministry_id,
                title        = EXCLUDED.title,
                doc_type     = EXCLUDED.doc_type,
                content_hash = EXCLUDED.content_hash,
                page_count   = EXCLUDED.page_count,
                ocr_used     = EXCLUDED.ocr_used,
                raw_path     = EXCLUDED.raw_path,
                fetched_at   = now(),
                status       = 'active'
            RETURNING id;
            """,
            (ministry_id, source_url, title, doc_type, content_hash,
             page_count, ocr_used, raw_path),
        )
        document_id = cur.fetchone()["id"]

        # Replace chunks wholesale to avoid stale content on re-ingest.
        cur.execute("DELETE FROM chunks WHERE document_id = %s;", (document_id,))
        for ch, vec in zip(chunks, vectors):
            content_h = sha256(ch["text"].encode("utf-8"))
            embedding = vec if vec.size > 0 else None
            cur.execute(
                """
                INSERT INTO chunks
                    (document_id, ministry_id, chunk_index, text, page, section,
                     token_count, embedding, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    document_id, ministry_id, ch["chunk_index"], ch["text"],
                    ch.get("page"), ch.get("section"), len(ch["text"]) // 4,
                    embedding, content_h,
                ),
            )
        conn.commit()
    return str(document_id), len(chunks)
