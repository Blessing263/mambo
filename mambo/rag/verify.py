"""Web-search verifier — triggered when the RAG answer hedges.

Tavily searches the web (Zimbabwe-scoped), then the configured generation model synthesizes
a short, clean, professional summary from the results. Never dumps raw URLs.
Result reads like a helpful officer who checked external sources — not a search
engine. Always preceded by a clear disclaimer that this is web-sourced, not an
allow-listed corpus document.
"""

from __future__ import annotations

import json
import os

import httpx
from openai import OpenAI

from shared.config import settings

TAVILY_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_URL = "https://api.tavily.com/search"

# Web verification is OFF by default so the allow-listed-source trust claim
# holds for the submission. Set RUZIVO_ENABLE_WEB_VERIFY=true (and TAVILY_API_KEY)
# to turn it on, e.g. for the live demo. See RUZIVO_AI4I_GAP_ANALYSIS.md (P0).
WEB_VERIFY_ENABLED = os.environ.get("RUZIVO_ENABLE_WEB_VERIFY", "").lower() in ("1", "true", "yes")

# DeepSeek pro — the reasoning model, better for synthesis from multiple sources
_pro = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

SYNTH_PROMPT = """You are a helpful research assistant for a Zimbabwe public-service \
information tool. Below are web search results about a citizen's question. \
Synthesize them into ONE short, clean, professional paragraph (3-5 sentences max) \
that answers the question. Follow these rules:

- Write like a helpful public-service assistant, not a search engine. Warm, clear, direct.
- Never mention "web search", "search results", "result #1", URLs, or source names.
- If multiple sources agree, state the information confidently.
- Filter out irrelevant, foreign, or clearly unofficial content (Reddit gossip, YouTube).
- If a source gives a procedure, summarize the key steps.
- If a source gives a cost, include it ("typically costs USD 10").
- Never use markdown headings (#, ##, ###). Use **bold** for emphasis instead.
- End with: "Always confirm with the official source."
- Output ONLY the paragraph, nothing else."""


def search_web(query: str, *, max_results: int = 5) -> list[dict]:
    if not TAVILY_KEY:
        return []
    try:
        resp = httpx.post(
            TAVILY_URL,
            json={"query": query, "max_results": max_results, "search_depth": "advanced"},
            headers={"Authorization": f"Bearer {TAVILY_KEY}"},
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        return (resp.json().get("results") or [])[:max_results]
    except Exception:
        return []


def synthesize(results: list[dict], question: str) -> str | None:
    """Use deepseek-v4-flash to write a clean synthesis from web results.
    Flash + higher token budget to handle reasoning overhead."""
    if not results:
        return None
    context = json.dumps(
        [{"title": r.get("title", ""), "snippet": r.get("content", "")[:400]} for r in results],
        ensure_ascii=False,
    )
    try:
        resp = _pro.chat.completions.create(
            model=settings.deepseek_model,  # flash — fast, reliable
            messages=[
                {"role": "system", "content": SYNTH_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nSearch results:\n{context}\n\nSynthesis:"},
            ],
            temperature=0.3,
            max_tokens=600,  # extra room for flash reasoning overhead
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception:
        return None


def verify_enrich(question: str, answer: str | None = None,
                  ministry_ids: list[str] | None = None) -> str | None:
    """Search the web and return a clean synthesis paragraph, or None.

    Disabled unless RUZIVO_ENABLE_WEB_VERIFY=true AND TAVILY_API_KEY is set, so the
    default deployment never blends non-official web content into an answer."""
    if not WEB_VERIFY_ENABLED or not TAVILY_KEY:
        return None
    results = search_web(f"{question} Zimbabwe government procedure official")
    if not results:
        return None
    synthesis = synthesize(results, question)
    if not synthesis:
        return None
    # Return clean text — no markdown dividers or italic disclaimers.
    # The frontend handles the "web verified" visual treatment.
    return synthesis
