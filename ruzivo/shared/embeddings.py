"""Embeddings via the isolated Ollama instance (Qwen3-Embedding-8B, 4096-dim, CPU).

Qwen3-Embedding works best when *queries* carry a short task instruction while
*documents* are embedded plain. We follow that convention: pass is_query=True when
embedding a user's question, and leave it False for document chunks.
"""

from __future__ import annotations

import httpx

from .config import settings

_QUERY_INSTRUCT = (
    "Instruct: Given a citizen's question about a Zimbabwe government ministry or "
    "public service, retrieve official document passages that answer it.\nQuery: "
)


def _format(texts: list[str], is_query: bool) -> list[str]:
    return [_QUERY_INSTRUCT + t for t in texts] if is_query else texts


def embed_batch(
    texts: list[str], *, is_query: bool = False, timeout: float = 300.0,
    dim: int | None = None,
) -> list[list[float]]:
    """Embed a batch of texts. First call may take ~40s while the model loads on CPU.
    If `dim` is given, the embedder is switched to match that dimension."""
    if not texts:
        return []
    model = _model_for_dim(dim)
    resp = httpx.post(
        f"{settings.ollama_base_url}/api/embed",
        json={"model": model, "input": _format(texts, is_query)},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    embeddings = data.get("embeddings")
    if not embeddings:
        raise RuntimeError(f"No embeddings returned from Ollama: {data!r}")
    # dim validation: only warn, don't block — multi-dim store uses both 768 and 4096
    return embeddings


def embed_text(text: str, *, is_query: bool = False, dim: int | None = None) -> list[float]:
    return embed_batch([text], is_query=is_query, dim=dim)[0]


# --- Query-embedding cache -------------------------------------------------------
# Citizens (and demo audiences) repeatedly ask the same starter questions. Caching
# the query vector turns those repeats from ~1.5s (CPU) into ~0µs. Per-process,
# bounded; document embeddings are never cached (they only run once at ingest).
from functools import lru_cache  # noqa: E402


@lru_cache(maxsize=2048)
def _query_vec_cached(normalized: str) -> tuple[float, ...]:
    return tuple(embed_text(normalized, is_query=True))


def embed_query(text: str) -> list[float]:
    """Embed a user question, served from cache on exact (normalized) repeats."""
    return list(_query_vec_cached(text.strip().lower()))


_MODEL_BY_DIM: dict[int, str] = {
    768: "nomic-embed-text",
    4096: "qwen3-embedding:8b",
}

def _model_for_dim(dim: int | None) -> str:
    if dim is None:
        return settings.embed_model
    model = _MODEL_BY_DIM.get(dim)
    if model:
        return model
    raise ValueError(f"No embedding model configured for dim={dim}. Known: {list(_MODEL_BY_DIM)}")
