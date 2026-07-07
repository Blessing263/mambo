"""The router ("traffic cop") — decide which ministry/ministries a question
belongs to, using the Registry keywords. Returns an ordered list (may be empty,
in which case retrieval runs unscoped and the answering ministries are inferred
from the retrieved chunks).
"""

from __future__ import annotations

from .catalog import ministries
from .matcher import KeywordMatcher


def _keyword_scores(question: str) -> dict[str, int]:
    q = f" {question.lower()} "
    scores: dict[str, int] = {}
    for m in ministries():
        s = KeywordMatcher(m["keywords"]).score(q)
        if s:
            scores[m["id"]] = s
    return scores


def route(question: str, *, max_ministries: int = 2) -> list[str]:
    scores = _keyword_scores(question)
    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [mid for mid, _ in ranked[:max_ministries]]
