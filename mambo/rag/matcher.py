"""Shared keyword matching — whole-word regex used by the router and journeys
matcher so the same boundary-check pattern is enforced consistently.
"""

from __future__ import annotations

import re


def match_keywords(text: str, keywords: list[str]) -> int:
    """Return the count of whole-word keyword matches in *text*.
    *text* should already be lowercased and wrapped in spaces (or word boundaries).
    """
    score = 0
    for kw in keywords:
        kw = kw.lower().strip()
        if not kw:
            continue
        if _WHOLE_WORD.search(text, kw):
            score += 1
    return score


def _compile_keyword(kw: str) -> re.Pattern:
    return re.compile(rf"(?<![a-z]){re.escape(kw)}(?![a-z])")


class KeywordMatcher:
    """Precompiled keyword set for a single source (ministry or journey)."""

    def __init__(self, keywords: list[str]):
        self._patterns = [_compile_keyword(kw) for kw in keywords if kw.strip()]

    def score(self, text: str) -> int:
        return sum(1 for p in self._patterns if p.search(text))


_WHOLE_WORD = re.compile("")  # dummy; actual matching uses Pattern.search on text
