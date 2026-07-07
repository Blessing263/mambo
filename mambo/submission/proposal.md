---
title: "Mambo"
track: "Development"
team: "Team Mambo"
lead: "Kundai Guvaza"
members: "Kundai Guvaza, Blessing B. Guvaza"
date: "3 July 2026"
project_id: "mambo"
---

::: cover
# Mambo

**Track:** Development — AI for Impact Challenge (AI4I 2026)

**Project Title:** Mambo — a whole-of-government citizen information assistant

**Team Name:** Team Mambo

**Lead Innovator:** Kundai Guvaza — Software Engineering student, TelOne Centre for Learning (TCFL)

**Team Members:** Kundai Guvaza (Lead), Blessing B. Guvaza

**Date:** 3 July 2026

**Live demo:** https://mambo.yttrix.tech (citizen chat) · https://mambo.yttrix.tech/admin (ministry portal)
:::

# 1. Problem Definition & Strategic Alignment

**The problem.** Zimbabwean citizens struggle to find reliable, plain-language
government information. Official content is scattered across many ministry
websites, frequently as scanned PDFs, written in legal jargon, and rarely answers
the *whole* question — what to bring, what it costs, where to go. Citizens do not
know which ministry handles what, so they make avoidable trips to the wrong
offices. The cost is wasted time, uneven access, and frustration — sharpest for
citizens on low-bandwidth mobile connections and for front-line registry staff who
answer the same questions all day.

**Who it serves.** Citizens applying for IDs, passports, certificates and tax
clearance; SME owners navigating business and tax registration; students and
journalists verifying laws and policies; and ministry helpdesk/registry staff who
need consistent, cited, first-line answers. A mobile-first, free, always-on
assistant reaches the widest audience.

**What Mambo is.** A retrieval-augmented assistant that answers in plain language
using **only** an allow-listed corpus of official documents, with a citation on
every claim, an honest **evidence-status badge** on every answer, structured
**service-journey cards** for common tasks, and a **ministry handoff card** when it
cannot answer. *Mambo* is a Shona word for "matters / affairs" — fitting for a
service that handles the public's business.

**Strategic alignment.** Mambo implements the National AI Strategy's goals for
inclusive, trustworthy public-service AI built on local capability and digital
sovereignty: official-source grounding with citations (trustworthy); abstention and
honest status (responsible); mobile-first free access (inclusive); a self-hostable
open-source stack with a CCE roadmap (sovereign, local). It is whole-of-government
— one brain, many ministries — led by ICT and designed so every ministry plugs in
via a curated registry. Each ministry also gets its own **customer-service portal** to see what citizens ask, curate vetted answers, and handle handoffs.

# 2. Technical Design & Product Logic

**Architecture** — three modules on different rhythms, meeting at one Knowledge
Store. Splitting by rhythm lets each scale independently:

```
 ingestion/ (batch)  ── discover · OCR · chunk · embed ──▶  PostgreSQL + pgvector
                                                             (Knowledge Store)
 webchat/  ──/api──▶  rag/ (FastAPI, per question)  ──route·retrieve·generate·trust──▶
 (Next.js 14)                                                        reads ▲
```

**Per-question pipeline:** `guard → intent → route → retrieve → (confident?) →
generate or fall back → trust layer`. The safety guard abstains before retrieval
(no LLM needed); generation sits behind a **swappable** OpenAI-compatible interface.

**Models and stack.**

| Component | Choice | Why |
|---|---|---|
| Generation | DeepSeek (flash), swappable | Phase 2 self-host an open-weight model on the CCE — no code change |
| Embeddings | Qwen3-Embedding-8B (4096-dim), self-hosted (Ollama) | Multilingual → Shona/Ndebele is an addition, not a re-embed |
| Knowledge store | PostgreSQL 16 + pgvector | Runs on a cheap cloud box *and* a Ministry server — one tech, two homes |
| Retrieval | Ministry-scoped cosine + recency boost | Newest version of an amended law wins |
| Webchat | Next.js 14, streaming SSE, mobile-first | Low-bandwidth, always-on |

**Data.** 889 official documents / 2,901 chunks from 9+ official sources
(5 ministries + ZIMRA, ZIMSEC, Veritas, ZimLII, + embassy/consulate procedure pages).
Every chunk stores source URL,
page, fetch date, content hash and raw path — so every citation is verifiable.

**Why AI is necessary (not a sledgehammer).** Plain-language synthesis, multi-
ministry routing, conversational follow-ups ("what about for schools?"), and cited
answers over many long documents cannot be met by keyword search, static FAQs, or
SQL. RAG is the appropriate, minimal use of AI: retrieve official passages and
ground generation in them. We do not apply AI where a rule would do.

**Product features (built).** Ministry routing ("find the right office"); inline
`[n]` citations on every answer; honest **evidence-status badge** (answered /
partial / unsupported / declined); a deterministic **abstention guard** (medical,
legal, personal-data, political, prompt-injection); **service-journey cards** for
six common tasks; **ministry handoff cards**; **live "thinking" steps** that narrate
the retrieval; streaming; mobile-first; light/dark themes; a **designed national
identity** (Spectral/Hanken typography, flag-palette tokens, a Seal/Mark/Wordmark);
and a **ministry customer-service portal** (`/admin`) with per-ministry login,
a scoped analytics dashboard (top questions, fallback rate, feedback), and
**reviewed-answer curation** — staff vet the top questions, and citizens get those
answers **instantly** (sub-second, zero LLM cost) via the reviewed-answer
short-circuit.

**Measured results (not asserted).** A fresh build from a clean checkout boots;
**67 automated tests pass**. On the corpus and a 32-question citizen-query set:

| Metric | Result |
|---|---|
| Router accuracy (English) | 89.3% routed to an expected ministry |
| Dangerous-case abstention | 7 / 7 handled correctly |
| Corpus integrity checks | 8 / 8 pass |
| Citation link liveness (sample) | 8 / 8 resolved |
| "Official-sources-only" claim | True (web verifier off by default) |
| Reviewed-answer latency | <1 s (instant, zero LLM) — curated by ministry staff |

Honest gaps are disclosed, not hidden: education (3 chunks) and ZimLII (1) are
thin; Shona/Ndebele router accuracy is 60% (Phase 2; embeddings are already
multilingual).

# 3. Deliverables & CCE Implementation Roadmap

**What is delivered.** A working **two-sided** product: a citizen-facing RAG
assistant (ingestion → retrieve → generate → trust) AND a ministry customer-service
portal (per-ministry login, analytics dashboard, reviewed-answer curation). Both
are deployed and demonstrable; the codebase includes 67 tests, a full evidence
pack, and a designed national identity system.

**Timeline (8 weeks of AI4I support).**

| Weeks | Workstream | Output |
|---|---|---|
| 1–2 | Harden | Close remaining security/schema/test items; run full RAG eval on resourced compute; fix accessibility "pending" items |
| 3–4 | Expand | Close coverage gaps (re-crawl education; expand ZimLII); add Shona/Ndebele registry keywords; measured sn/nd pilot |
| 5–8 | Pilot | Home Affairs pilot: confirm sources + handoff contacts, reviewed-answer cache, controlled user group, weekly review, go/no-go |

**ZCHPC CCE roadmap.** The stack is CCE-ready by design (open-source, self-hostable,
swappable model interface). On the CCE we run PostgreSQL+pgvector (the Knowledge
Store), bulk embedding jobs on GPU (`ingestion/embed_bulk.py` already targets a
remote GPU Ollama endpoint), a self-hosted open-weight generation model behind the
swappable interface, and the evaluation pipeline. Migration is a re-point of
`OLLAMA_BASE_URL` / `DEEPSEEK_BASE_URL` — no code change.

| CCE milestone | Outcome |
|---|---|
| Provision | CCE partition: Postgres+pgvector + Ollama/vLLM endpoints |
| Migrate | Move the Knowledge Store to CCE (dump/restore; same schema) |
| Re-embed | Bulk embeddings on GPU; run full evaluation |
| Benchmark | Latency/cost vs current local+API setup; publish metrics |
| Operate | Incremental refresh + monitoring from CCE |

This removes per-query API cost and keeps data in-country. **Mambo is cloud-deployed
today, not edge**; the CCE is the documented scale/sovereignty path, and
mobile-first low-bandwidth is the user-facing strategy.

# 4. Compliance & Risk Mitigation

**Data Protection Act [Chapter 12:07].**

| Obligation | How Mambo handles it |
|---|---|
| Lawful basis | Public official documents (low personal-data risk) |
| Data minimisation | Query log keeps only needed fields; `client_ip`/`user_agent` retention-bounded |
| Retention & deletion | Defined retention window + deletion workflow (planned PII redaction) |
| Access control | Restricted log access by role |
| Transparency | User notice: do not enter ID/medical/private information |
| Open-data release | **Not** claimed for query logs |

**Cybersecurity.** Nonce challenge (single-use) on write endpoints; origin lock to
the official app; per-IP rate limiting + concurrent-stream cap; bot user-agent
blocklist + behaviour/entropy checks; validated input sizes; docs/redoc disabled in
production; secrets never committed. The deterministic abstention guard and
official-sources-only retrieval harden the content layer. (67 tests cover nonce,
abstention, security, schema, and the reviewed-answer streaming path.) The admin
portal adds **session-cookie auth** (bcrypt, httpOnly, SameSite-Lax, ministry-scoped
SQL so staff only see their own data; rate-limited login; generic 401).

**Responsible AI.** Mandatory citations; a confidence threshold below which Mambo
does not guess; the evidence-status badge; abstention for out-of-scope/unsafe
questions with a referral (clinician / Law Society / ministry); per-section "not
specified" in journeys; recency boost for amended laws; a risk register and
monitoring plan with drift detection (PSI/KL) and a rule-baseline fallback.

**Key risks** (full register in `submission/deployment/risk_register.csv`):
hallucination (grounding + evidence status + abstention); coverage gaps (disclosed,
being closed); latency on local hosting (CCE roadmap); local-language inequity
(honestly disclosed, Phase 2); PII in queries (minimisation + redaction plan).

# 5. Sustainability & Future Adoption

**Cost reality.** Infrastructure is inexpensive (~USD 50/month at pilot); the real
cost is people — a reviewer per ministry batch and part-time engineering
(`submission/business/cost_model.csv`). The stack is open-source and self-hostable,
so a Ministry can run it on its own servers with **no per-query API cost** once on
the CCE.

**Adoption path.** Pilot with one ministry (Home Affairs proposed) under AI4I
milestone support → per-ministry onboarding (repeatable, via
`ministry_onboarding_pack.md`) → whole-of-government rollout (the registry is the
keystone) → embeddable widget on live ministry sites + low-bandwidth channels
(WhatsApp).

**Maintainability.** Incremental refresh re-ingests only changed documents; a
quarterly re-verification cadence; the **reviewed-answer cache** — now live in the
admin portal, where ministry staff curate the top questions and citizens get those
answers instantly (sub-second, no LLM call); monitoring that drives what to fix
next.

---

**A note on fallibility.** Mambo is a **guidance and routing assistant**, not a
replacement for official decisions, professional advice, or ministry confirmation.
It points citizens to the right office and the right documents, and it says so
honestly when the official record does not cover a question. That scope discipline
is how it earns trust.
