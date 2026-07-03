"""The router ("traffic cop") — decide which ministry/ministries a question
belongs to, using the Registry keywords. Returns an ordered list (may be empty,
in which case retrieval runs unscoped and the answering ministries are inferred
from the retrieved chunks).
"""

from __future__ import annotations

import re

from .catalog import ministries


def _keyword_scores(question: str) -> dict[str, int]:
    q = f" {question.lower()} "
    scores: dict[str, int] = {}
    for m in ministries():
        score = 0
        for kw in m["keywords"]:
            kw = kw.lower().strip()
            if not kw:
                continue
            # whole-word/phrase match to avoid spurious substring hits
            if re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", q):
                score += 1
        if score:
            scores[m["id"]] = score
    return scores


def route(question: str, *, max_ministries: int = 2) -> list[str]:
    scores = _keyword_scores(question)
    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [mid for mid, _ in ranked[:max_ministries]]
