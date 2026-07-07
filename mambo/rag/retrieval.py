"""Retrieval — embed the question (Qwen 4096-dim, local CPU, ~1.5s warm) and run
an exact cosine search over the Knowledge Store, optionally scoped to ministries.

When multiple versions of the same document exist (e.g. Labour Act 2003, 2005,
2019, 2025), the most recently fetched version is ranked higher via a recency
boost. This ensures citizens always get the current law, not a superseded version.
"""

from __future__ import annotations

import numpy as np

from shared.config import settings
from shared.db import get_conn
from shared.embeddings import embed_query

# Fetch more candidates than needed so the recency re-ranker can promote newer docs.
_OVERSAMPLE = settings.retrieval_oversample

_BASE_SQL = """
    SELECT c.id, c.ministry_id, c.text, c.page, c.section,
           d.title AS doc_title, d.source_url, d.published_date, d.fetched_at,
           1 - (c.embedding <=> %(qvec)s) AS score
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    {where} AND c.embedding IS NOT NULL
    ORDER BY c.embedding <=> %(qvec)s
    LIMIT %(k)s;
"""


def _recency_boost(results: list[dict], k: int) -> list[dict]:
    """Re-rank: when two chunks come from different versions of the same document
    (same base title, different year/date), boost the newer one.

    Uses fetched_at as a proxy for recency — newer documents were ingested from
    more recently published official sources.
    """
    if not results:
        return results

    # Group by a normalised title key (strip year suffixes, "updated to YYYY", etc.)
    import re
    def _base_title(title: str) -> str:
        t = (title or "").lower().strip()
        # Strip source suffix
        t = re.sub(r"\|\s*veritaszim\s*$", "", t).strip()
        # Strip parenthetical year info: "(updated to 2019)", "(2005)"
        t = re.sub(r"\s*\(updated to \d{4}\)", "", t)
        t = re.sub(r"\s*\(\d{4}\)", "", t)
        # Strip trailing date: "16-09-2025", ", 2003"
        t = re.sub(r"\s*\d{1,2}-\d{2}-\d{4}\s*$", "", t)
        t = re.sub(r",?\s*\d{4}\s*$", "", t)
        # Unify chapter formats: "chapter:" → "[chapter" and ensure brackets
        t = re.sub(r"\s*chapter:\s*", " [chapter ", t)
        if "[chapter" in t and "]" not in t:
            t = t.rstrip() + "]"
        # Strip "act" qualifiers: "amendment act" stays, but normalize whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t

    # For each base title, find the newest fetched_at
    from collections import defaultdict
    newest: dict[str, object] = {}
    for r in results:
        base = _base_title(r.get("doc_title", ""))
        fa = r.get("fetched_at")
        if base not in newest or (fa and fa > newest[base]):
            newest[base] = fa

    # Apply a small score boost to the newest version of each doc family
    boosted = []
    for r in results:
        base = _base_title(r.get("doc_title", ""))
        is_newest = (r.get("fetched_at") == newest.get(base))
        # Boost the newest version; penalise older versions of the same doc
        adj = r["score"] + (0.05 if is_newest else -0.03)
        boosted.append({**r, "score": adj})

    boosted.sort(key=lambda x: x["score"], reverse=True)
    return boosted[:k]


def search(question: str, ministry_ids: list[str] | None = None, k: int = 6) -> list[dict]:
    qvec = np.asarray(embed_query(question), dtype=np.float32)
    where = ""
    params: dict = {"qvec": qvec, "k": k * _OVERSAMPLE}
    if ministry_ids:
        where = "WHERE c.ministry_id = ANY(%(ministries)s)"
        params["ministries"] = list(ministry_ids)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(_BASE_SQL.format(where=where), params)
        results = cur.fetchall()
    return _recency_boost(results, k)
