# Mambo 🇿🇼

**A plain-language, citizen-facing information assistant for Zimbabwe public services.**

Ask a question in everyday words and get a clear answer drawn from the allow-listed
public-service corpus — with the source always shown. Live demo:
**https://mambo.yttrix.tech**

*Mambo* means "king" in Shona; here it is framed as the **king of information**.

---

## What it does

- **Whole-of-government-ready**: one assistant across multiple ministries and official bodies
  (ICT, Health, Home Affairs, Finance, Education) plus adjacent legal/tax sources
  (Veritas — Acts & Statutory Instruments, ZIMRA — tax, ZIMSEC — exams).
- **Grounded & cited**: answers come only from retrieved source documents, with a
  clickable source on every reply. When the documents don't cover something, it says
  so honestly and points to the ministry's contact details.
- **Smart routing** ("find the right office"): figures out which ministry/agency a
  question belongs to and answers from their documents.
- **Human-reviewed answers**: ministry staff can curate high-volume questions so
  vetted answers bypass model generation and stay consistent.
- **Feedback loop**: citizens can rate answers; staff can search query logs and
  inspect ministry-scoped analytics for unanswered demand.
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
  behind a swappable interface, trust layer, admin portal API, reviewed-answer cache,
  feedback endpoint, and abuse protections.
- **`webchat/`** — Next.js + owned chat components; branded, streaming, ministry picker.
- **`registry/`** — the Ministry Registry: source of truth + the scrape allow-list.
- **`shared/`** — config, pooled DB access, and embeddings used by both ingestion and RAG.

See **[FOUNDATION.md](FOUNDATION.md)** for the full design and architecture decisions.

## Stack

Python (uv) · FastAPI · Next.js · PostgreSQL + pgvector · Ollama (Qwen3-Embedding-8B,
4096-dim) · DeepSeek (generation) · nginx + Let's Encrypt.

## Production hardening

- Central environment-based configuration in `shared/config.py`; production mode is
  the default unless `RUZIVO_ENV=development` is set.
- PostgreSQL access uses a thread-safe `psycopg_pool.ConnectionPool`.
- Public API routes include rate limits, browser/nonce checks for ask endpoints,
  origin checks on writes, and bounded concurrent streams.
- LLM output is sanitized before it reaches the browser while preserving markdown
  source citations such as `[1]`.
- Admin endpoints are ministry-scoped, rate-limited, parameterized, and use secure
  session cookies.
- Reviewed-answer cache is invalidated on admin create/update/delete so newly
  curated answers are served immediately.
- CI in `.github/workflows/test.yml` runs the Python test suite plus webchat type
  checks/build on push and pull requests.

## Deployment files

The repository includes production scaffolding:

- `Dockerfile` and `docker-compose.yml` for Postgres + pgvector, Ollama, and the API.
- `deploy/nginx/mambo.yttrix.tech.conf` for the public reverse proxy and SSE support.
- `deploy/systemd/mambo-api.service` and `deploy/systemd/mambo-web.service` for VPS
  process management.
- `scripts/backup.sh` for PostgreSQL backups with optional remote upload.

Current VPS routing for `mambo.yttrix.tech`:

- nginx listens publicly on `:80` and `:443` via the local SNI listener on
  `127.0.0.1:8443`.
- `https://mambo.yttrix.tech/` proxies to `mambo-web.service`, a Next.js production
  server on `127.0.0.1:3056`.
- `https://mambo.yttrix.tech/api/*` proxies to `mambo-api.service`, FastAPI/Uvicorn on
  `127.0.0.1:8771`; proxy buffering is disabled for streaming responses.
- The API needs a non-empty `DATABASE_URL` and should run from the same Python
  environment used by the project tests so `psycopg_pool` is available.

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

## Tests

```bash
uv run pytest tests/ -q
cd webchat && npm run build
```

> Configuration has sensible code defaults in `shared/config.py`; override via env vars.
> The DeepSeek API key is read from `DEEPSEEK_API_KEY` or `~/.secrets/deepseek-api-key`.
