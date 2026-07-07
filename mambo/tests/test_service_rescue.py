"""Scope-mismatch rescue — a question asked under the wrong ministry scope
(stale focus chip, mid-chat topic change, router miss) must still find the
ministry that actually holds the answer instead of dead-ending."""

from __future__ import annotations

import rag.service as service


def _patch_search(monkeypatch, scoped, unscoped):
    def fake_search(q, ministries, k=8):
        return unscoped if ministries is None else scoped
    monkeypatch.setattr(service.retrieval, "search", fake_search)
    monkeypatch.setattr(service.trust, "assess",
                        lambda rs: bool(rs) and rs[0]["score"] > 0.5)


def test_scoped_miss_rescues_to_owning_ministry(monkeypatch):
    # Scoped to home_affairs the shelf is empty-ish; unscoped, ICT holds the Act.
    scoped = [{"ministry_id": "home_affairs", "score": 0.1}]
    unscoped = [{"ministry_id": "ict", "score": 0.9}]
    _patch_search(monkeypatch, scoped, unscoped)
    detected, results, confident = service._retrieve_with_rescue(
        "what are my rights under the data protection law", ["home_affairs"])
    assert confident
    assert detected == ["ict"]
    assert results == unscoped


def test_weakly_confident_wrong_shelf_is_overridden(monkeypatch):
    # The real failure: generic ministry pages score above the confidence
    # threshold (0.598) but the Act lives elsewhere and scores far higher (0.833).
    scoped = [{"ministry_id": "home_affairs", "score": 0.598}]
    unscoped = [{"ministry_id": "ict", "score": 0.833}]
    _patch_search(monkeypatch, scoped, unscoped)
    detected, results, confident = service._retrieve_with_rescue(
        "what are my rights under the data protection law", ["home_affairs"])
    assert confident
    assert detected == ["ict"]
    assert results == unscoped


def test_confident_scoped_answer_is_not_second_guessed(monkeypatch):
    # Same top chunk both ways (correctly scoped question) — scope is kept.
    scoped = [{"ministry_id": "home_affairs", "score": 0.663}]
    unscoped = [{"ministry_id": "home_affairs", "score": 0.663}]
    _patch_search(monkeypatch, scoped, unscoped)
    detected, results, confident = service._retrieve_with_rescue(
        "how do i replace a lost id", ["home_affairs"])
    assert confident
    assert detected == ["home_affairs"]
    assert results == scoped


def test_unscoped_miss_stays_honest(monkeypatch):
    # Nothing anywhere → no rescue, stays unconfident (falls back to handoff).
    weak = [{"ministry_id": "ict", "score": 0.1}]
    _patch_search(monkeypatch, weak, weak)
    detected, results, confident = service._retrieve_with_rescue(
        "something the corpus does not cover", ["ict"])
    assert not confident
    assert detected == ["ict"]
