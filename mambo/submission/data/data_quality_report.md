# Mambo Corpus — Data Quality Report

**Dataset:** Mambo Official-Source Knowledge Corpus · **Version:** v1.0.0 (registry 2026-06-07)
**Collection period:** June 2026 · **Report generated:** live via `scripts/validate_corpus.py`

## Summary

| Metric | Value |
|---|---|
| Enabled sources | 9 (5 ministries + 4 adjacent) |
| Documents | 903 |
| Chunks | 3,059 |
| Embeddings complete | 99.97% (3,058/3,059; 1 pending) |
| Documents using OCR | 8 |
| Duplicate source URLs | 0 |
| Orphan chunks | 0 |
| Off-allow-list sources | 0 |

**Validation status: PASS** (all eight automated integrity checks green). Honest coverage gaps are disclosed below; they do not affect integrity but do affect representativeness.

## Quality dimensions

- **Completeness.** 100% of documents carry a title and raw_path; 99.97% of chunks are embedded (one chunk is pending embed in the deferred-embedding workflow). The schema now permits nullable embeddings precisely to support that workflow.
- **Accuracy / provenance.** Every document stores its canonical `source_url`, `content_hash` (SHA-256 of raw bytes), `raw_path` (saved original), `fetched_at`, and `ocr_used` flag. Citations resolve to these fields, so every claim is verifiable back to the official source.
- **Consistency.** Sources are drawn only from the registry allow-list (`registry/ministries.json`); chunk `ministry_id` is denormalised and FK-constrained; controlled `source_type` vocabulary (`ministry` / `adjacent`).
- **Validity.** Typed schema; FK constraints with `ON DELETE CASCADE`; `UNIQUE(source_url)`; vector dimension fixed at 4096 with a `dim` label column.
- **Uniqueness.** `source_url` is unique by constraint and by check (0 duplicates); chunk-level `content_hash` supports dedupe.
- **Timeliness.** Incremental refresh keyed on `content_hash` re-processes only changed documents; `fetched_at` tracks recency; retrieval applies a recency boost so the newest version of a repeatedly-amended document (e.g. an Act) ranks first.
- **Integrity.** 0 orphan chunks; every chunk resolves to a document and a ministry.

## Bias and representativeness (disclosed honestly)

Chunk coverage is uneven across sources:

| Source | Chunks | Note |
|---|---|---|
| zimra | 857 | heaviest |
| finance | 490 | |
| ict | 465 | |
| veritas | 393 | |
| home_affairs | 342 | |
| zimsec | 307 | |
| health | 201 | |
| **education** | **3** | **thin — site yielded little extractable text; needs re-crawl** |
| **zimlii** | **1** | **very thin — judgment ingest is a separate pipeline; needs expansion** |

Other notes: OCR was applied to only 8 documents (most PDFs were text-based); local-language (Shona/Ndebele) source documents are scarce. Router accuracy on English citizen questions is 89.3% but drops on Shona/Ndebele phrasings (local-language routing is Phase 2).

## Privacy

The corpus is public official documents (no personal data solicited). User queries are logged separately in `query_log`; `client_ip`/`user_agent` are retention-bounded operational fields and the policy provides for PII minimisation, a retention window, and a deletion workflow (see the proposal compliance section and the asset/license register).

## Corrective actions

1. Re-crawl education and expand the ZimLII judgment pipeline to close the coverage gaps above.
2. Increase scanned-PDF OCR coverage where source documents are image-based.
3. Run the full RAG evaluation (`scripts/evaluate_mambo.py --full`) to capture citation coverage, fallback rate, and latency alongside the deterministic router accuracy already recorded.
4. Add a Shona/Ndebele source-document pilot once local-language sources are identified.

## Evidence

- `submission/data/validation_report.json` — machine-readable check results (regenerable via `scripts/validate_corpus.py`).
- `submission/data/router_accuracy.csv` — per-question routing verdicts.
- `submission/data/source_register.csv`, `submission/data/metadata_cards.json`, `submission/data/data_dictionary.csv`.
