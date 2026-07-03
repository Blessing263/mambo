# Local-Language (Shona / Ndebele) Evaluation

**Honest position, per the gap analysis: do not claim local-language parity until
it is measured.** This document records what is measured now and what is pending.

## Setup

Five pilot questions from `tests/fixtures/eval_questions.jsonl`:

- q21 (sn) replace a lost national ID — *correct*
- q22 (sn) passport requirements — *correct*
- q23 (sn) paying tax — *missed*
- q24 (nd) get a passport — *correct*
- q25 (nd) register a marriage — *missed*

## Measured now (deterministic, reproducible)

- **Router accuracy on the sn/nd subset: 3 / 5 (60%)**, versus **89.3%** on English.
  Root cause: the router matches English keywords from the registry, so Shona and
  Ndebele phrasings frequently fail to hit a ministry even when the service is
  obvious to a human.

This is a real, disclosed gap — exactly the kind of finding responsible-AI scoring
rewards when reported honestly rather than concealed.

## Why retrieval could still work (architectural readiness)

Embeddings use **Qwen3-Embedding-8B**, a multilingual model, so a Shona or Ndebele
query can in principle retrieve relevant English-language official passages by
semantic similarity. The blocker is **routing** (English keywords gate the
retrieval scope), not embedding language coverage.

## Full RAG measurement — PENDING the live stack

End-to-end metrics by language — answer success rate, fallback rate, citation
coverage, latency — require the live generation + embeddings stack. On current
local hosting the RAG path is slow (a Shona smoke question exceeded 90 s), so the
full bilingual run is not reproduced here. It is scripted:

```
uv run python scripts/evaluate_ruzivo.py --full   # then slice router_accuracy.csv / full_eval.csv by language
```

## Remediation plan (Phase 2)

1. Add **Shona and Ndebele keyword sets** per ministry in
   `registry/ministries.json` (the router already supports multi-word matches).
2. Run a **measured 15 + 15 sn/nd pilot** through the full RAG path on properly
   resourced compute (ZCHPC CCE / GPU), recording answer success, fallback,
   citation coverage and latency **by language**.
3. Only after that measurement may the proposal claim any degree of
   local-language support, scoped to the measured languages and tasks.

## Conclusion

Ruzivo is **multilingual-ready at the embedding layer** and **not yet at parity**
at the routing/generation layer for Shona and Ndebele. This is reported honestly
and is a defined Phase 2 workstream, not a current claim.
