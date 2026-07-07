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

# flash is a reasoning model that "thinks" for ~20-30s before emitting the answer.
# The endpoint accepts `thinking: {type: disabled}` to skip reasoning — ~3x faster
# first token, with equivalent cited/structured quality. Applied to every call.
_NO_THINK = {"thinking": {"type": "disabled"}}

# Strip stale [n] citation markers from prior assistant turns so the model doesn't
# echo source numbers that don't match the current turn's sources.
_CITE = re.compile(r"\[\d+\]")
HISTORY_TURNS = settings.history_turns


def _safe_choice(resp) -> str:
    """Extract content safely; returns '' if choices is empty (API error / refusal)."""
    if not resp.choices:
        return ""
    return resp.choices[0].message.content or ""


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


def _messages(question: str, contexts: list[dict], history: list[dict] | None,
              journey: dict | None = None) -> list[dict]:
    system = SYSTEM_PROMPT
    if journey:
        from .prompt import journey_directive  # noqa: PLC0415
        system = system + journey_directive(journey)
    return [
        {"role": "system", "content": system},
        *_history_messages(history),
        {"role": "user", "content": build_user_prompt(question, contexts)},
    ]


# Cheap regex pre-gate: obvious greetings/thanks/capability skip the LLM call
# entirely (instant reply, no classify latency, no wasted retrieval).
_QUICK_INTENT: list[tuple[str, re.Pattern]] = [
    ("greeting", re.compile(r"^\s*(hi|hie|hey+|hello+|good\s+(morning|afternoon|evening|day)|how\s+(are|r)\s+(you|u)|mangwanani|sekalenge|mhoro)\b[\s!.?]*$", re.I)),
    ("thanks", re.compile(r"^\s*(thanks|thank\s+you|thx|thankx|cheers|appreciated|much\s+appreciated|nice\s+one|ta)\b[\s!.?]*$", re.I)),
    ("capability", re.compile(r"^\s*(what\s+can\s+you\s+do|who\s+are\s+you|what\s+are\s+you|what\s+do\s+you\s+do|how\s+do\s+you\s+work|are\s+you\s+(a\s+|an\s+)?(bot|ai|robot|human)|what(?:'s|\s+is)\s+your\s+name)\??\s*$", re.I)),
]


def classify_intent(question: str) -> str:
    """Classify user intent BEFORE retrieval. Catch greetings, thanks,
    capability questions, and off-topic messages so RAG is never wasted.
    Returns one of: greeting, thanks, capability, off_topic, question, other.

    Obvious greetings/thanks/capability are caught by a regex pre-gate (no LLM).
    flash is a reasoning model — it spends tokens "thinking" before producing
    visible content, so the budget must be large enough for both reasoning
    AND the output word (typically 100–200 tokens)."""
    q = (question or "").strip()
    for intent, rx in _QUICK_INTENT:
        if rx.match(q):
            return intent
    resp = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": INTENT_PROMPT.format(question=question)},
        ],
        temperature=0,
        max_tokens=200,
        extra_body=_NO_THINK,
    )
    raw = (_safe_choice(resp) or "").strip().lower()
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
        max_tokens=400,
        extra_body=_NO_THINK,
    )
    rewritten = (_safe_choice(resp) or "").strip()
    return rewritten or question


def generate(
    question: str,
    contexts: list[dict],
    *,
    history: list[dict] | None = None,
    journey: dict | None = None,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> str:
    resp = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=_messages(question, contexts, history, journey),
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body=_NO_THINK,
    )
    return (_safe_choice(resp) or "").strip()


def generate_stream(
    question: str,
    contexts: list[dict],
    *,
    history: list[dict] | None = None,
    journey: dict | None = None,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> Iterator[str]:
    stream = _client.chat.completions.create(
        model=settings.deepseek_model,
        messages=_messages(question, contexts, history, journey),
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        extra_body=_NO_THINK,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
