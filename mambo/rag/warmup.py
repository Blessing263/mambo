"""Embedding model warmup — runs at startup so the first citizen query doesn't
pay the ~13s CPU cold-start penalty for Qwen3-Embedding-8B.
"""

from __future__ import annotations

_DEMO_QUESTIONS = [
    "How do I replace a lost national ID?",
    "How do I apply for a passport?",
    "How do I get a tax clearance certificate?",
    "How do I register a birth certificate?",
    "How do I register a business for tax?",
    "How do I check exam results or replace a certificate?",
    "What is the National AI Strategy?",
    "What taxes do employers pay?",
]


def warmup_embeddings() -> None:
    """Load the embedding model and pre-warm the query cache for demo questions."""
    try:
        from shared.embeddings import embed_query  # noqa: PLC0415
        embed_query("warmup")
        for q in _DEMO_QUESTIONS:
            try:
                embed_query(q)
            except Exception:
                pass
    except Exception:
        pass
