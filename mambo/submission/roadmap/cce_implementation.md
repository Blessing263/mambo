# ZCHPC CCE Implementation Roadmap

The Zimbabwe Centre for High-Performance Computing (ZCHPC) Controlled Compute
Environment (CCE) is the path to running Mambo on national, sovereign compute —
removing per-query API cost, improving latency, and keeping data in-country.

## What can run on the CCE

| Workload | Why CCE | Notes |
|---|---|---|
| **PostgreSQL + pgvector** (Knowledge Store) | Persistent, relational, vector search | Same schema runs on cloud today; migrate to CCE-hosted instance |
| **Bulk embedding jobs** (Qwen3-Embedding-8B) | CPU-slow (~16s/chunk), GPU-fast (~0.1s/chunk) | `ingestion/embed_bulk.py` already supports a remote GPU Ollama endpoint |
| **Self-hosted generation** (open-weight LLM) | Removes DeepSeek API cost/latency | The generation interface is swappable; point `DEEPSEEK_BASE_URL` at a CCE-hosted model |
| **Evaluation pipeline** | Batch, periodic | `scripts/evaluate_mambo.py --full`, `validate_corpus.py` on resourced compute |
| **Reviewed-answer cache curation assist** | Batch | Future: assist reviewers with grounded drafts |

## Compute requirements (estimate — to confirm with ZCHPC)

- **Embedding bulk job:** 1× GPU (e.g. A100/L4 class) for a few minutes per full
  corpus re-embed (2,901 chunks, expected seconds-to-minutes on GPU); or CPU for incremental.
- **Self-hosted generation:** 1–2× GPU sized to the chosen open-weight model and
  target p95 latency; or CPU-only for low concurrency.
- **Postgres+pgvector:** CPU + RAM + SSD; exact sizing depends on corpus growth.
- **Storage:** raw corpus (270 MB now) + DB + backups; modest at demo scale.

## Milestones

1. **Provision** a CCE partition: Postgres+pgvector + an Ollama (or vLLM) endpoint
   serving Qwen3-Embedding-8B and a chosen open-weight generation model.
2. **Migrate** the Knowledge Store to CCE Postgres (dump/restore; same schema).
3. **Repoint** `OLLAMA_BASE_URL` (embeddings) and `DEEPSEEK_BASE_URL`/model
   (generation) at CCE endpoints — no code changes (swappable interfaces).
4. **Bulk re-embed** on CCE GPU; run the full evaluation there.
5. **Benchmark** latency/cost vs the current local+API setup; publish metrics.
6. **Operate** ingestion (incremental refresh) + monitoring from CCE.

## Dependencies

- ZCHPC access + GPU quota + persistent storage + egress to official source sites
  (for crawling) — all standard CCE asks.
- A selected open-weight generation model with an OpenAI-compatible serving endpoint
  (Ollama/vLLM) so the swappable interface works unchanged.

## Honesty

Mambo is **cloud-deployed today, not edge.** The CCE roadmap is the documented
scale/sovereignty path, not a current claim. Mobile-first, low-bandwidth design is
the user-facing strategy; offline/edge is explicitly future work.
