"""Streaming SSE end-to-end (LLM + DB mocked): full answer, citations, hedged
contacts, chatty path, low-confidence fallback."""

from __future__ import annotations

import json

import rag.llm as llm
import rag.service as service
import rag.trust as trust

UA = {"User-Agent": "Mozilla/5.0 (MamboTest)"}

CTX = [
    {"doc_title": "AI Strategy", "page": 12, "source_url": "https://ict.gov.zw/a",
     "ministry_id": "ict", "text": "ctx"},
    {"doc_title": "Data Protection", "page": 4, "source_url": "https://ict.gov.zw/b",
     "ministry_id": "ict", "text": "ctx"},
]


def _stub_confident(monkeypatch, tokens):
    monkeypatch.setattr(service, "prepare_stream",
        lambda q, h, ministry_filter=None: {"results": CTX, "detected": ["ict"],
                                            "confident": True, "history": h or []})
    monkeypatch.setattr(service, "_log_stream", lambda *a, **k: None)
    monkeypatch.setattr(llm, "generate_stream",
        lambda q, ctx, *, history=None, **k: iter(tokens))


def _events(client, nonce):
    out = []
    with client.stream("POST", "/ask/stream",
                       json={"question": "q", "nonce": nonce}, headers=UA) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if line.startswith("data: "):
                out.append(json.loads(line[6:]))
    return out


def test_full_answer_streamed_with_correct_citations(client, reset_security, get_nonce, monkeypatch):
    _stub_confident(monkeypatch, ["The fee is USD 10 [1]. ", "Bring ID [2]."])
    events = _events(client, get_nonce())
    deltas = "".join(e["text"] for e in events if e["type"] == "delta")
    done = next(e for e in events if e["type"] == "done")
    assert deltas == "The fee is USD 10 [1]. Bring ID [2]."   # full text streamed
    assert [c["title"] for c in done["citations"]] == ["AI Strategy", "Data Protection"]
    assert done["service_journey"] is None  # field always present; stub has no journey


def test_hedged_answer_attaches_contacts(client, reset_security, get_nonce, monkeypatch):
    monkeypatch.setattr(trust, "by_id",
        lambda mid: {"ict": {"short_name": "ICT", "contact": {"phone": "1"}}}.get(mid))
    _stub_confident(monkeypatch, ["I do not have the exact fee [1]. "])
    events = _events(client, get_nonce())
    deltas = "".join(e["text"] for e in events if e["type"] == "delta")
    done = next(e for e in events if e["type"] == "done")
    assert deltas == "I do not have the exact fee [1]. "   # answer still streamed (no empty reply)
    assert done["fallback_contact"] is not None            # contacts safety-net fired


def test_chatty_path(client, reset_security, get_nonce, monkeypatch):
    monkeypatch.setattr(service, "prepare_stream",
        lambda q, h, ministry_filter=None: {"chatty_response": "Hi there!",
                                            "confident": True, "history": []})
    monkeypatch.setattr(service, "_log_stream", lambda *a, **k: None)
    events = _events(client, get_nonce())
    deltas = "".join(e["text"] for e in events if e["type"] == "delta")
    done = next(e for e in events if e["type"] == "done")
    assert deltas == "Hi there!"
    assert done["confident"] is True and done["citations"] == []


def test_low_confidence_fallback(client, reset_security, get_nonce, monkeypatch):
    monkeypatch.setattr(trust, "by_id",
        lambda mid: {"ict": {"short_name": "ICT", "contact": {"phone": "1"}}}.get(mid))
    monkeypatch.setattr(service, "prepare_stream",
        lambda q, h, ministry_filter=None: {"results": CTX, "detected": ["ict"],
                                            "confident": False, "history": h or []})
    events = _events(client, get_nonce())
    deltas = "".join(e["text"] for e in events if e["type"] == "delta")
    done = next(e for e in events if e["type"] == "done")
    assert done["confident"] is False
    assert done["fallback_contact"] is not None
    assert "ICT" in deltas
