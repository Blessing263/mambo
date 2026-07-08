# Mambo 🇿🇼

**A whole-of-government-ready, plain-language citizen information assistant for Zimbabwe public services.**

Ask a question in everyday words and get a clear answer drawn from the allow-listed
public-service corpus — with the source always cited. Submitted to the POTRAZ
**AI for Impact Challenge (AI4I 2026), Track 3 — Development**.

> *Mambo* means "king" in Shona; here it is framed as the **king of information**:
> it routes a question to the right covered source, answers from retrieved
> public-service documents, names the source, and hands you to the right office
> when the corpus doesn't cover it.

## Where things are

```
mambo/                     ← the product (everything below is in here)
├── ingestion/             discover · OCR · chunk · embed (batch)
├── rag/                   route · retrieve · generate · trust (FastAPI)
├── webchat/               Next.js 14 streaming chat (mobile-first)
├── registry/              ministry registry + allow-list + service journeys
├── shared/                config · db · embeddings · schema
├── tests/                 pytest suite (80 pass, 1 integration skipped by default) + eval fixtures
├── scripts/               validate_corpus · evaluate_mambo · check_citation_links · render_proposal
└── submission/            Track 3 proposal PDF + full evidence pack (appendices)
```

Start with **[`mambo/FOUNDATION.md`](mambo/FOUNDATION.md)** (architecture & decisions),
**[`mambo/README.md`](mambo/README.md)** (quick start), and the
**[proposal PDF](mambo/submission/mambo_AI4I_Proposal_Development.pdf)**.

## What makes it trustworthy

- **Allow-listed-source-only** — retrieval from a curated corpus of ministry,
  agency, and public legal sources; the web verifier is off by default.
- **Cited** — every factual claim carries an inline `[n]` citation to its source.
- **Honest evidence status** — every answer is badged *answered / partial /
  unsupported / declined*; it never guesses.
- **Abstains** from medical diagnosis, legal advice, personal-data lookups, political
  opinion, and prompt injection — with a referral to the right human.
- **Service journeys** — common tasks (lost ID, passport, tax clearance, birth
  certificate…) answered as structured whole-problem cards.
- **Ministry handoff** — when it can't answer, it routes you to the exact office.

## Quick start

```bash
cd mambo
uv sync
uv run python registry/load_registry.py          # sync registry -> DB
uv run python -m ingestion.pipeline --ministry ict
uv run uvicorn rag.api:app --port 8770            # local-dev RAG API
cd webchat && npm install && npm run dev          # local-dev webchat
uv run pytest tests/ -q                           # 80 pass, 1 skipped
```

See `mambo/FOUNDATION.md` for the architecture and design decisions.

## Status

Working end-to-end MVP; 80 backend tests pass with 1 integration test skipped by
default; the live corpus currently reports 9 ministries, 890 documents, and
2,901 chunks through `/api/health`. Honest gaps (coverage, local-language parity)
are documented in `mambo/submission/`. Tracked responsibly on `main`.
