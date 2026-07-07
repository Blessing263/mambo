"""Citizen feedback endpoint: targets one query_log row without live Postgres."""

from __future__ import annotations

import rag.api as api

UA = {"User-Agent": "Mozilla/5.0 (MamboTest)"}


class _Cur:
    def __init__(self):
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return {"id": "00000000-0000-0000-0000-000000000001"}


class _Conn:
    def __init__(self, cur):
        self.cur = cur
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True


def test_feedback_with_session_updates_latest_matching_row(client, reset_security, monkeypatch):
    cur = _Cur()
    conn = _Conn(cur)
    monkeypatch.setattr(api, "get_conn", lambda: conn)

    r = client.post(
        "/feedback",
        json={"session_id": "s1", "question": "How do I renew a passport?", "feedback": 1},
        headers=UA,
    )

    assert r.status_code == 200
    assert "WITH target AS" in cur.sql
    assert "ORDER BY asked_at DESC" in cur.sql
    assert "LIMIT 1" in cur.sql
    assert cur.params == ("s1", "How do I renew a passport?", 1)
    assert conn.committed


def test_feedback_without_session_updates_latest_question_match(client, reset_security, monkeypatch):
    cur = _Cur()
    conn = _Conn(cur)
    monkeypatch.setattr(api, "get_conn", lambda: conn)

    r = client.post(
        "/feedback",
        json={"question": "How do I renew a passport?", "feedback": -1},
        headers=UA,
    )

    assert r.status_code == 200
    assert "WITH target AS" in cur.sql
    assert "ORDER BY asked_at DESC" in cur.sql
    assert "LIMIT 1" in cur.sql
    assert cur.params == ("How do I renew a passport?", -1)
    assert conn.committed


def test_feedback_rejects_blank_question(client, reset_security):
    r = client.post("/feedback", json={"question": "   ", "feedback": 1}, headers=UA)
    assert r.status_code == 422
