# Security Test Report

## Controls implemented

| Layer | Control | Where |
|---|---|---|
| Bot protection | Nonce challenge (single-use, 5-min TTL) required on `/ask` + `/ask/stream`; frontend refreshes per-ask with one retry | `rag/security.py`, `rag/api.py`, `webchat/lib/api.ts` |
| Origin lock | Only the official app origins are accepted (`RUZIVO_ALLOWED_ORIGINS`) | `rag/security.py::_origin_check` |
| Rate limiting | Sliding-window per-IP (`/ask`, `/nonce`, `/health`, `/ministries`) + concurrent-stream cap (5/IP) | `rag/security.py` |
| Bot UA blocklist | python-requests, curl, wget, scrapy, zgrab, etc. blocked; browser UA required; sec-fetch-site consistency | `rag/security.py::_bot_check` |
| Behaviour | Sub-500ms cadence + low-entropy + over-long-question detection per session | `rag/security.py::_behavior_check` |
| Input limits | Question ≤ 2000 chars; history ≤ 20 turns; validated (Pydantic); no docs/redoc in prod | `rag/api.py` |
| Content safety | Deterministic abstention guard (medical, legal, personal-data, political, prompt-injection) before retrieval; system-prompt topic-lock; allow-listed source corpus | `rag/guard.py`, `rag/prompt.py` |
| Allow-listed only | Tavily web verifier OFF by default (`RUZIVO_ENABLE_WEB_VERIFY`); retrieval only from allow-listed registry domains | `rag/verify.py`, `ingestion/allowlist.py` |
| Secrets | DeepSeek key read from env / `~/.secrets`, never committed; `.env` gitignored | `shared/config.py`, `.gitignore` |
| Errors | Generic error bodies; no stack-trace leakage | `rag/api.py` exception handlers |

## Automated test coverage

`tests/test_security.py` and `tests/test_guard.py` verify (hermetically, no LLM/DB):
- nonce required (403 without), single-use (403 on reuse), refreshable (200 on fresh);
- blocked user-agents rejected (403);
- entropy and rapid-cadence behaviour flags;
- abstention for each unsafe category (prompt-injection, medical, legal,
  personal-data, political) and that a safe national-ID question is **not** declined;
- end-to-end streaming abstention (guard short-circuits before the LLM).

Full suite: **59 passed**.

## Results

- All security/abstention tests pass.
- Corpus allow-list discipline: **0** off-allow-list sources (`validation_report.json`).
- Tavily disabled by default → no open-web content reaches answers.

## Residual risks & next steps

- Move in-memory security state (nonce, rate-limit) to Redis for multi-worker /
  multi-host (single-process today).
- Add dedicated prompt-injection and rate-limit penetration test scripts (currently
  covered by unit tests + the guard).
- Add PII redaction on `query_log` before retention (policy defined, implementation
  planned).
- CORS/origin and output-sanitisation (citation-only grounding) integration tests.
