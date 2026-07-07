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


def test_reviewed_answer_respects_active_ministry_filter(monkeypatch):
    service.invalidate_reviewed_cache()

    class Cur:
        row = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, _sql, params):
            if params == ("how do i apply for a passport?",):
                self.row = {
                    "ministry_id": "home_affairs",
                    "answer": "Passport answer",
                    "citations": [],
                }
            elif params == ("how do i apply for a passport?", "home_affairs"):
                self.row = {
                    "ministry_id": "home_affairs",
                    "answer": "Passport answer",
                    "citations": [],
                }
            else:
                self.row = None

        def fetchone(self):
            return self.row

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return Cur()

    monkeypatch.setattr(service, "get_conn", lambda: Conn())

    try:
        assert service.get_reviewed("How do I apply for a passport?", "finance") is None
        assert service.get_reviewed("How do I apply for a passport?", "home_affairs")["source_ministry"] == ["home_affairs"]
        assert service.get_reviewed("How do I apply for a passport?")["source_ministry"] == ["home_affairs"]
    finally:
        service.invalidate_reviewed_cache()


def test_reviewed_cache_invalidation_allows_new_admin_answers(monkeypatch):
    service.invalidate_reviewed_cache()
    service._rev_known = set()
    service._rev_known_loaded = True
    calls = {"db": 0}

    class Cur:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, _sql, _params=None):
            calls["db"] += 1

        def fetchone(self):
            return {
                "ministry_id": "home_affairs",
                "answer": "Passport answer",
                "citations": [],
            }

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return Cur()

    monkeypatch.setattr(service, "get_conn", lambda: Conn())

    try:
        assert service.get_reviewed("How do I apply for a passport?") is None
        assert calls["db"] == 0

        service.invalidate_reviewed_cache()

        reviewed = service.get_reviewed("How do I apply for a passport?")
        assert reviewed["source_ministry"] == ["home_affairs"]
        assert calls["db"] == 1
    finally:
        service.invalidate_reviewed_cache()
