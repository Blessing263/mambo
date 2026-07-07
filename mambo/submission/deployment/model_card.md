# Mambo — Model & System Card

## Overview

Mambo is a retrieval-augmented citizen information assistant for Zimbabwe
public-service information. It answers plain-language questions using **only** the
retrieved documents from an allow-listed corpus of ministry, agency, tax,
education, and public legal sources, with inline citations, an honest evidence-status badge on
every answer, structured service-journey cards, and a handoff card when it cannot
answer.

## Components

| Component | Model / tech | Role |
|---|---|---|
| Generation | DeepSeek (flash) behind a **swappable** OpenAI-compatible interface; Phase 2 can self-host an open-weight model | Writes the plain-language answer from retrieved passages |
| Embeddings | **Qwen3-Embedding-8B** (4096-dim), self-hosted via Ollama — multilingual | Semantic retrieval (query + chunks) |
| Knowledge store | PostgreSQL 16 + pgvector (exact cosine at 4096-dim) | Chunks tagged by ministry, full provenance |
| Retrieval | Ministry-scoped cosine search + recency boost (newest version wins) | Grounds every answer |
| Routing | Keyword classifier over the ministry registry | "Find the right office" |
| Trust layer | Confidence threshold (0.45), mandatory citations, abstention guard, fallback/handoff | Honest, safe answers |

## Intended use

Citizens, SMEs, students, journalists, and ministry helpdesk staff asking
factual questions about Zimbabwe government services, policies, laws, fees, and
procedures. Web (mobile-first) today; embeddable widget + low-bandwidth channels
(WhatsApp) planned.

## Out of scope (enforced)

The safety guard abstains from: medical diagnosis, legal conclusions,
personal-data lookups, political opinions, and prompt injection. Mambo does not
process payments, authenticate users, or access case-specific records.

## Data

- **Corpus:** 890 documents / 2,901 chunks from 9 allow-listed sources
  (5 ministries + ZIMRA, ZIMSEC, Veritas, ZimLII). Provenance (source URL,
  page, fetch date, content hash, raw path) stored per chunk.
- **Queries:** logged for analytics/quality under a minimisation policy
  (retention-bounded `client_ip`/`user_agent`; no solicited personal data).

## Evaluation (measured)

- Router accuracy **89.3%** (English); abstention **7/7** dangerous cases correct;
- Corpus integrity **8/8** checks; citation links **8/8** sample resolved.
- Full per-question RAG metrics (citation coverage, fallback, latency) scripted,
  pending a resourced (CCE/GPU) run.

## Limitations (disclosed honestly)

- **Coverage gaps:** education (3 chunks) and zimlii (1) are thin.
- **Local language:** routing is English-keyword; Shona/Ndebele router accuracy
  60% (embeddings are multilingual-ready; parity is Phase 2, not claimed).
- **Latency:** on current local hosting the RAG path is slow; addressed by the
  CCE / self-host roadmap.
- **Currency:** depends on official sites staying current; incremental refresh
  re-ingests changed documents.

## Fairness & ethics

Honest evidence-status badge on every answer (answered / partial / unsupported /
declined); per-section "not specified" rather than guessing; recency boost so
amended laws return the current version; abstention with referral to a clinician /
the Law Society / the relevant ministry.

## Monitoring & contact

See `monitoring_plan.md` and `risk_register.csv`. Steward: Mambo team
(see proposal cover page).
