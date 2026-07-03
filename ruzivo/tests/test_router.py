"""Router — keyword → ministry routing. Hermetic (catalog mocked at the use site)."""

from __future__ import annotations

from rag import router

# Minimal ministry records — router only reads `id` and `keywords`.
SAMPLE = [
    {"id": "ict", "keywords": ["internet", "ai strategy", "data protection", "artificial intelligence"]},
    {"id": "home_affairs", "keywords": ["passport", "national id", "birth certificate"]},
    {"id": "finance", "keywords": ["tax", "budget", "paye"]},
]


def _mock(monkeypatch):
    # router does `from .catalog import ministries` — patch the bound name on router.
    monkeypatch.setattr(router, "ministries", lambda: SAMPLE)


def test_passport_routes_home_affairs(monkeypatch):
    _mock(monkeypatch)
    assert "home_affairs" in router.route("how do I replace a lost passport?")


def test_ai_strategy_routes_ict(monkeypatch):
    _mock(monkeypatch)
    assert "ict" in router.route("what is the national ai strategy?")


def test_tax_routes_finance(monkeypatch):
    _mock(monkeypatch)
    assert "finance" in router.route("how do I pay income tax?")


def test_unknown_returns_empty(monkeypatch):
    _mock(monkeypatch)
    assert router.route("xyzzy frobnicate") == []


def test_caps_at_max_ministries(monkeypatch):
    _mock(monkeypatch)
    assert len(router.route("passport tax internet", max_ministries=2)) <= 2


def test_whole_word_match_no_false_substring(monkeypatch):
    """'tax' inside 'taxonomy' must NOT route to finance."""
    _mock(monkeypatch)
    assert router.route("explain taxonomy classification") == []
