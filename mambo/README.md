# Mambo 🇿🇼

**A plain-language, citizen-facing information assistant for the Government of Zimbabwe.**

Ask a question in everyday words and get a clear answer drawn **only** from official
government documents — with the source always shown. Live demo:
**https://mambo.yttrix.tech**

*Mambo* means "knowledge" in Shona.

---

## What it does

- **Whole-of-government**: one assistant across multiple ministries and official bodies
  (ICT, Health, Home Affairs, Finance, Education) plus adjacent legal/tax sources
  (Veritas — Acts & Statutory Instruments, ZIMRA — tax, ZIMSEC — exams).
- **Grounded & cited**: answers come only from retrieved official documents, with a
  clickable source on every reply. When the documents don't cover something, it says
  so honestly and points to the ministry's contact details.
- **Smart routing** ("find the right office"): figures out which ministry/agency a
  question belongs to and answers from their documents.
- **Conversational**: remembers the last few turns so follow-ups ("what about for
  schools?") resolve correctly.
- **Streaming, multi-user, mobile-first.**

## Architecture (three modules + a shared store)

```
 ingestion/  ── discover · scrape · OCR · chunk · embed ──▶  Postgres + pgvector
   (Module 3, batch)                                          (Knowledge Store)
                                                                     ▲ reads
 webchat/  ──API──▶  rag/  ── route · retrieve · DeepSeek · trust ───┘
 (Module 1, Next.js) (Module 2, FastAPI)
```

- **`ingestion/`** — polite, allow-list-scoped crawler + headless-browser harvester
  (Playwright) for JS/CDN-protected sites. Embedding is deferrable for bulk GPU runs.
- **`rag/`** — FastAPI: ministry router, exact pgvector search, DeepSeek generation
  behind a swappable interface, and the trust layer (citations, confidence, topic-lock).
- **`webchat/`** — Next.js + owned chat components; branded, streaming, ministry picker.
- **`registry/`** — the Ministry Registry: source of truth + the scrape allow-list.
- **`shared/`** — config, DB, and embeddings used by both ingestion and RAG.

See **[FOUNDATION.md](FOUNDATION.md)** for the full design and architecture decisions.

## Stack

Python (uv) · FastAPI · Next.js · PostgreSQL + pgvector · Ollama (Qwen3-Embedding-8B,
4096-dim) · DeepSeek (generation) · nginx + Let's Encrypt.

## Quick start

```bash
# Knowledge Store: Postgres 16 + pgvector, database `ruzivo` (see shared/db/schema.sql)
# Embeddings: Ollama serving qwen3-embedding:8b (DeepSeek key at ~/.secrets/deepseek-api-key)
uv sync
uv run python registry/load_registry.py
uv run python -m ingestion.pipeline --ministry ict
uv run uvicorn rag.api:app --port 8770
cd webchat && npm install && npm run dev
```

> Configuration has sensible code defaults in `shared/config.py`; override via env vars.
> The DeepSeek API key is read from `DEEPSEEK_API_KEY` or `~/.secrets/deepseek-api-key`.
