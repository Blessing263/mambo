# Ministry Onboarding Pack

How a ministry moves from "in the registry" to "live in Ruzivo with a confirmed
handoff." Designed so onboarding is repeatable and ministry staff can do most of it
without developer help.

## 1. Source approval

- Confirm the ministry's **official domains** and add them to the registry
  `domains` allow-list (the crawler and the "official-sources-only" claim depend on it).
- Confirm the **seed URLs** (homepage + known publication pages) and any curated
  `doc_pages`.
- Record the source type (`ministry`) and, for adjacent bodies, `source_type:
  adjacent` + `parent_ministry`.

## 2. Fallback / handoff contact confirmation

- Confirm **phone, WhatsApp, email, address, office hours** against the ministry's
  own published contact page.
- Confirm a **service portal / counter** URL.
- Set `last_verified_at` to today and assign a **`human_review_owner`** (the person
  accountable for keeping this ministry's data current).
- Do not enable the ministry until the handoff contact is confirmed.

## 3. Pilot scope (per ministry)

- In-scope services for the pilot (e.g. for Home Affairs: passport, national ID,
  birth/death/marriage certificates).
- Out-of-scope for the pilot (e.g. case-specific status, which requires auth).
- Success criteria (e.g. route accuracy ≥ 90% on the ministry's eval questions;
  citation coverage ≥ 80%; broken-link rate = 0).
- Fallback/escalation path and the office that owns pilot queries.

## 4. Review cadence

- **Quarterly** contact + source re-verification.
- **On change:** re-crawl when the ministry homepage structure changes; re-verify
  contacts when a source link breaks (`check_citation_links.py`).
- Eval re-run after each material corpus change (`scripts/evaluate_ruzivo.py`).

## 5. Launch checklist

- [ ] Domains allow-listed; seed URLs confirmed.
- [ ] At least one ingestion run succeeds for the ministry
      (`uv run python -m ingestion.pipeline --ministry <id>`).
- [ ] Chunk count > 0 and embedding completeness = 100%
      (`scripts/validate_corpus.py`).
- [ ] Handoff contact confirmed; `last_verified_at` set; review owner assigned.
- [ ] Eval questions for the ministry route correctly and cite the ministry's docs.
- [ ] Cited source URLs resolve (`scripts/check_citation_links.py`).
- [ ] Ministry marked `enabled: true`; smoke test on the live assistant passes.
