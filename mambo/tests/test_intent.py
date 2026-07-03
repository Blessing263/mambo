"""Intent gate — chatty_response mapping (pure; classify_intent is mocked elsewhere)."""

from __future__ import annotations

import rag.llm as llm


def test_greeting_has_response():
    assert llm.chatty_response("greeting") is not None


def test_thanks_has_response():
    assert llm.chatty_response("thanks") is not None


def test_capability_has_response():
    assert llm.chatty_response("capability") is not None


def test_off_topic_has_response():
    assert llm.chatty_response("off_topic") is not None


def test_question_returns_none():
    assert llm.chatty_response("question") is None


def test_other_returns_none():
    assert llm.chatty_response("other") is None
