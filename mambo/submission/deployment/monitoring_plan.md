# Monitoring Plan

## What is logged today

Every question writes a row to `query_log`: `session_id`, `question`, `lang`,
`detected_ministries`, `confident`, `answered`, `citations` (json), `latency_ms`,
`client_ip`, `user_agent` (the last two retention-bounded). The streaming path also
records `evidence_status` / `service_journey` context via the done-meta.

## Metrics to surface (dashboard)

**Quality**
- Route accuracy (expected vs detected ministry) — from the eval set, run on change.
- Citation coverage: share of answerable answers with ≥1 citation.
- Fallback / `unsupported` rate; `declined` rate (abstention) by category.
- Evidence-status mix (answered / partial / unsupported / declined).
- 👍/👎 feedback rate.

**Performance**
- Latency: p50, p95, max (end-to-end and per stage: route → embed → retrieve →
  generate). Target p95 after CCE/GPU self-host.
- Token usage per answer (generation cost proxy).
- Error rate (5xx, timeouts, aborts).

**Drift (Phase 2)**
- **PSI / KL-divergence** on the distribution of (a) query topics and (b) top
  retrieval cosine scores, compared to a baseline window. Alert when PSI > 0.2 or
  KL exceeds threshold.

**Coverage / trust**
- Broken citation links (`check_citation_links.py`), per ministry.
- Chunks-by-ministry balance; embedding NULL rate (should be 0).
- Top unanswered questions → feeds corpus expansion priorities.

## Thresholds & alerts

| Metric | Alert condition | Action |
|---|---|---|
| Fallback rate | > 30% over 24h | Review corpus coverage / router |
| p95 latency | > target post-CCE | Investigate stage; scale compute |
| Broken links | any cited URL 4xx/5xx | Re-crawl + re-verify contact |
| Drift (PSI) | > 0.2 | Investigate query/topic shift; consider rule-baseline fallback |
| Error rate | > 2% | Page on-call; check services |
| Prompt-injection `declined` spike | sharp rise | Review for attack pattern |

## Fallback trigger

If drift or error rate exceeds critical thresholds, Mambo can fall back to a
rule-based / reviewed-answer baseline (the `reviewed_answers` table is present for
exactly this forward-compatible path) rather than serve degraded generation.

## Review cadence

- **Daily:** latency, error rate, feedback.
- **Weekly:** evidence-status mix, fallback rate, top unanswered questions.
- **Quarterly:** full eval re-run, contact + source re-verification, drift review.

Sample log/dashboards to be produced from `query_log`; the metrics above define the
schema extensions needed (route_scores, retrieval_scores, fallback_reason,
token_count) tracked in the gap analysis.
