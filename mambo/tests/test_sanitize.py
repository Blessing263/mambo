"""LLM output sanitisation should remove HTML/script injection, not citations."""

from __future__ import annotations

from rag.sanitize import sanitize


def test_sanitize_preserves_markdown_citations():
    text = "Renew at the registry office [1]. Bring ID [2]."
    assert sanitize(text) == text


def test_sanitize_strips_script_style_tags_and_event_attrs():
    dirty = (
        "Safe [1]. <script>alert(1)</script><style>body{display:none}</style>"
        '<a onclick="steal()" href="javascript:alert(1)">Click</a>'
    )
    cleaned = sanitize(dirty)

    assert "Safe [1]." in cleaned
    assert "<script" not in cleaned
    assert "<style" not in cleaned
    assert "onclick" not in cleaned
    assert "javascript:" not in cleaned.lower()
