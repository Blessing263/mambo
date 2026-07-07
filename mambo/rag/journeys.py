"""Service Journey Mode — match a citizen's question to a high-demand service
journey so the answer can be shaped into a structured whole-problem card
(eligibility, what to bring, steps, fees, where, timeline).

Section CONTENT stays grounded in official documents via RAG; the journey only
shapes structure. If no journey matches, the normal RAG answer is used unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

from .matcher import KeywordMatcher

_JOURNEYS = json.loads(
    (Path(__file__).resolve().parent.parent / "registry" / "journeys.json").read_text()
)["journeys"]


def all_journeys() -> list[dict]:
    return _JOURNEYS


def match_journey(question: str) -> dict | None:
    """Return the best-matching journey (highest whole-word keyword hit count), or None."""
    q = f" {question.lower()} "
    best: dict | None = None
    best_score = 0
    for j in _JOURNEYS:
        score = KeywordMatcher(j.get("keywords", [])).score(q)
        if score > best_score:
            best_score = score
            best = j
    return best
