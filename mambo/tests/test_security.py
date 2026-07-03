"""Security: nonce lifecycle (required, single-use), UA blocking, behaviour guards."""

from __future__ import annotations

import rag.llm as llm
import rag.service as service
import rag.security as security

UA = {"User-Agent": "Mozilla/5.0 (MamboTest)"}


def _stub_chatty(monkeypatch):
    """Make the 200 path hermetic (no LLM/DB)."""
    monkeypatch.setattr(service, "prepare_stream",
        lambda q, h, ministry_filter=None: {"chatty_response": "ok",
                                            "confident": True, "history": []})
    monkeypatch.setattr(service, "_log_stream", lambda *a, **k: None)
    monkeypatch.setattr(llm, "generate_stream",
        lambda q, ctx, *, history=None, **k: iter(["x"]))


def test_no_nonce_rejected(client, reset_security):
    r = client.post("/ask/stream", json={"question": "q"}, headers=UA)
    assert r.status_code == 403


def test_valid_nonce_accepted_then_consumed(client, reset_security, get_nonce, monkeypatch):
    _stub_chatty(monkeypatch)
    n = get_nonce()
    with client.stream("POST", "/ask/stream", json={"question": "q", "nonce": n}, headers=UA) as r:
        assert r.status_code == 200
        for _ in r.iter_lines():
            pass
    # same nonce again -> 403 (single-use)
    r2 = client.post("/ask/stream", json={"question": "q", "nonce": n}, headers=UA)
    assert r2.status_code == 403


def test_blocked_user_agent(client, reset_security, get_nonce):
    r = client.post("/ask/stream", json={"question": "q", "nonce": get_nonce()},
                    headers={"User-Agent": "python-requests/2.31"})
    assert r.status_code == 403


def test_text_entropy_low_for_garbage():
    assert security._text_entropy("aaaaaaaaaaaaaaa") < 2.0


def test_text_entropy_high_for_real_words():
    assert security._text_entropy("how do I renew my passport in harare") > 2.0


def test_behavior_blocks_rapid_same_session(reset_security):
    assert security._behavior_check("s1", "first question here") is True
    assert security._behavior_check("s1", "second question fast") is False  # <0.5s gap
