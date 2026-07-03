"""Trust layer — confidence threshold, citation shape, contacts, fallback."""

from __future__ import annotations

import rag.trust as trust


def _mock_by_id(monkeypatch, mapping):
    # trust does `from .catalog import by_id` — patch the bound name on trust.
    monkeypatch.setattr(trust, "by_id", lambda mid: mapping.get(mid))


def test_assess_below_threshold():
    assert trust.assess([{"score": 0.30}]) is False


def test_assess_at_threshold():
    assert trust.assess([{"score": 0.45}]) is True


def test_assess_empty():
    assert trust.assess([]) is False


def test_cite_shape():
    c = trust.cite({"doc_title": "AI Strategy", "page": 12,
                    "source_url": "https://ict.gov.zw/a", "ministry_id": "ict"})
    assert c == {"title": "AI Strategy", "page": 12,
                 "url": "https://ict.gov.zw/a", "ministry": "ict"}


def test_top_citations_limits():
    ctx = [{"doc_title": f"d{i}", "page": i, "source_url": f"u{i}", "ministry_id": "ict"}
           for i in range(5)]
    assert len(trust.top_citations(ctx, n=3)) == 3


def test_contacts_known_ministry(monkeypatch):
    _mock_by_id(monkeypatch,
                {"ict": {"id": "ict", "short_name": "ICT", "contact": {"phone": "123"}}})
    out = trust._contacts(["ict"])
    assert out and out[0]["ministry"] == "ICT" and out[0]["phone"] == "123"


def test_contacts_unknown_ministry(monkeypatch):
    _mock_by_id(monkeypatch, {})
    assert trust._contacts(["nope"]) == []


def test_fallback_response_has_contact(monkeypatch):
    _mock_by_id(monkeypatch,
                {"ict": {"id": "ict", "short_name": "ICT", "contact": {"phone": "123"}}})
    fb = trust.fallback_response("how do I pay tax?", ["ict"])
    assert fb["confident"] is False
    assert fb["citations"] == []
    assert fb["fallback_contact"]          # contact attached
    assert "ICT" in fb["answer"]           # ministry named in the fallback text
