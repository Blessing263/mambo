"""Embeddings — OpenAI first (text-embedding-3-large, 3072-dim), Ollama fallback.

Provider priority: when an OpenAI key is available (OPENAI_API_KEY or
~/.secrets/openai-api-key) and EMBED_PROVIDER != "ollama", texts are embedded
via the OpenAI API. Without a key — or if EMBED_PROVIDER=ollama — we fall back
to the isolated Ollama instance (Qwen3-Embedding-8B, 4096-dim, CPU), which is
also what the historical corpus was embedded with.

IMPORTANT: vectors from different models live in different spaces. The chunks
`dim` column labels each vector's model space; switching providers requires
re-embedding the corpus (ingestion.embed_bulk).

Qwen3-Embedding works best when *queries* carry a short task instruction while
*documents* are embedded plain; OpenAI models take the raw text for both. Pass
is_query=True when embedding a user's question.
"""

from __future__ import annotations

import time

import httpx

from .config import settings

_QUERY_INSTRUCT = (
    "Instruct: Given a citizen's question about a Zimbabwe government ministry or "
    "public service, retrieve official document passages that answer it.\nQuery: "
)

# Ollama models by dimension — the fallback path and the multi-dim store.
_OLLAMA_MODEL_BY_DIM: dict[int, str] = {
    768: "nomic-embed-text",
    4096: "qwen3-embedding:8b",
}

_OPENAI_RETRIES = 4  # 429/5xx backoff: 2s, 4s, 8s, 16s
_RETRYABLE = (429, 500, 502, 503, 529)


def _use_openai(dim: int | None) -> bool:
    if settings.embed_provider == "ollama" or not settings.openai_api_key:
        return False
    # An explicit dim that only Ollama serves (multi-dim store) wins.
    if dim is not None and dim != settings.embed_dim and dim in _OLLAMA_MODEL_BY_DIM:
        return False
    return True


def _embed_openai(texts: list[str], *, dim: int | None, timeout: float) -> list[list[float]]:
    body = {
        "model": settings.openai_embed_model,
        "input": texts,
        "dimensions": dim or settings.embed_dim,
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    last_exc: Exception | None = None
    for attempt in range(_OPENAI_RETRIES + 1):
        try:
            resp = httpx.post(
                f"{settings.openai_base_url}/embeddings",
                json=body, headers=headers, timeout=timeout,
            )
            if resp.status_code in _RETRYABLE:
                raise httpx.HTTPStatusError(
                    f"retryable {resp.status_code}", request=resp.request, response=resp
                )
            resp.raise_for_status()
            data = resp.json()["data"]
            # The API preserves input order; sort by index defensively anyway.
            return [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status not in _RETRYABLE:
                raise  # 401/400/… — retrying won't help
            last_exc = exc
            if attempt < _OPENAI_RETRIES:
                time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"OpenAI embeddings failed after retries: {last_exc}")


def _embed_ollama(texts: list[str], *, is_query: bool, dim: int | None,
                  timeout: float) -> list[list[float]]:
    formatted = [_QUERY_INSTRUCT + t for t in texts] if is_query else texts
    requested_dim = dim or settings.embed_dim
    resp = httpx.post(
        f"{settings.ollama_base_url}/api/embed",
        json={"model": _ollama_model_for_dim(requested_dim), "input": formatted},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    embeddings = data.get("embeddings")
    if not embeddings:
        raise RuntimeError(f"No embeddings returned from Ollama: {data!r}")
    return embeddings


def embed_batch(
    texts: list[str], *, is_query: bool = False, timeout: float = 300.0,
    dim: int | None = None,
) -> list[list[float]]:
    """Embed a batch of texts via the priority provider (OpenAI → Ollama).
    If `dim` is given, the provider/model serving that dimension is used."""
    if not texts:
        return []
    if _use_openai(dim):
        return _embed_openai(texts, dim=dim, timeout=timeout)
    return _embed_ollama(texts, is_query=is_query, dim=dim, timeout=timeout)


def embed_text(text: str, *, is_query: bool = False, dim: int | None = None) -> list[float]:
    return embed_batch([text], is_query=is_query, dim=dim)[0]


# --- Query-embedding cache -------------------------------------------------------
# Citizens (and demo audiences) repeatedly ask the same starter questions. Caching
# the query vector turns those repeats into ~0µs — and, on OpenAI, saves the API
# call. Per-process, bounded; document embeddings are never cached (they only run
# once at ingest).
from functools import lru_cache  # noqa: E402


@lru_cache(maxsize=2048)
def _query_vec_cached(normalized: str) -> tuple[float, ...]:
    return tuple(embed_text(normalized, is_query=True))


def embed_query(text: str) -> list[float]:
    """Embed a user question, served from cache on exact (normalized) repeats."""
    return list(_query_vec_cached(text.strip().lower()))


def _ollama_model_for_dim(dim: int | None) -> str:
    if dim is None:
        dim = settings.embed_dim
    model = _OLLAMA_MODEL_BY_DIM.get(dim)
    if model:
        return model
    raise ValueError(
        f"No Ollama embedding model configured for dim={dim}. "
        "For the OpenAI 3072-dim corpus, provide OPENAI_API_KEY or set "
        "EMBED_PROVIDER=ollama with EMBED_DIM=4096 and a 4096-dim database. "
        f"Known Ollama dims: {list(_OLLAMA_MODEL_BY_DIM)}"
    )
