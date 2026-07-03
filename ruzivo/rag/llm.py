"""DeepSeek behind a swappable interface (OpenAI-compatible API).

Only this module knows which LLM answers. Phase 2 can point base_url/model at a
Ministry-hosted open-weight model with no change elsewhere.

Conversation memory: `rewrite_query` turns a context-dependent follow-up
("what about for schools?") into a standalone search query using the history, and
generation receives the recent turns so answers stay coherent — while remaining
grounded in the freshly retrieved sources for the current question.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from openai import OpenAI

from shared.config import settings

from .prompt import (
    CAPABILITY_RESPONSE, GREETING_RESPONSE, INTENT_PROMPT, INTENT_SYSTEM,
    OFF_TOPIC_RESPONSE, REWRITE_SYSTEM, SYSTEM_PROMPT, THANKS_RESPONSE,
    build_rewrite_user, build_user_prompt,
)

_client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

# Strip stale [n] citation markers from prior assistant turns so the model doesn't
# echo source numbers that don't match the current turn's sources.
_CITE = re.compile(r"\[\d+\]")
HISTORY_TURNS = 6  # last 6 messages (~3 exchanges)


def _history_messages(history: list[dict] | None) -> list[dict]:
    if not history:
        return []
    out: list[dict] = []
    for turn in history[-HISTORY_TURNS:]:
        role = turn.get("role")
        content = turn.get("content", "")
        if role not in ("user", "assistant") or not content:
            continue
        if role == "assistant":
            content = _CITE.sub("", content).strip()
        out.append({"role": role, "content": content})
    return out


def _messages(question: str, contexts: list[dict], history: list[dict] | None) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *_history_messages(history),
        {"role": "user", "content": build_user_prompt(question, contexts)},
    ]


def classify_intent(question: str) -> str:
    """Classify user intent BEFORE retrieval. Catch greetings, thanks,
    capability questions, and off-topic messages so RAG is never wasted.
    Returns one of: greeting, thanks, capability, off_topic, question, other.

    flash is a reasoning model — it spends tokens "thinking" before producing
    visible content, so the budget must be large enough for both reasoning
    AND the output word (typically 100–200 tokens)."""
    resp = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": INTENT_PROMPT.format(question=question)},
        ],
        temperature=0,
        max_tokens=200,  # room for reasoning + the single-word answer
    )
    raw = (resp.choices[0].message.content or "").strip().lower()
    # The model may output "greeting." or " intent: greeting" — normalise.
    for token in ("greeting", "thanks", "capability", "question", "off_topic"):
        if token in raw:
            return token
    return "other"


def chatty_response(intent: str) -> str | None:
    """Return a pre-written response for non-question intents, or None."""
    if intent == "greeting":
        return GREETING_RESPONSE
    if intent == "thanks":
        return THANKS_RESPONSE
    if intent == "capability":
        return CAPABILITY_RESPONSE
    if intent == "off_topic":
        return OFF_TOPIC_RESPONSE
    return None


def rewrite_query(question: str, history: list[dict] | None) -> str:
    """Resolve references in a follow-up into a standalone retrieval query.
    No history → returns the question unchanged (no extra LLM call)."""
    if not history:
        return question
    resp = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM},
            {"role": "user", "content": build_rewrite_user(question, history[-HISTORY_TURNS:])},
        ],
        temperature=0,
        # flash is a reasoning model — it spends tokens "thinking" first, so a small
        # budget yields empty content. Give it room for reasoning + the short query.
        max_tokens=400,
    )
    rewritten = (resp.choices[0].message.content or "").strip()
    return rewritten or question


def generate(
    question: str,
    contexts: list[dict],
    *,
    history: list[dict] | None = None,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> str:
    resp = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=_messages(question, contexts, history),
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def generate_stream(
    question: str,
    contexts: list[dict],
    *,
    history: list[dict] | None = None,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> Iterator[str]:
    stream = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=_messages(question, contexts, history),
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
