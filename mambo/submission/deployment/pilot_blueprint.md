# Pilot Blueprint — Ministry of Home Affairs and Cultural Heritage

> Concrete example pilot. Home Affairs is chosen because it owns the richest set
> of service journeys already implemented (lost national ID, passport, birth
> certificate) — the clearest citizen-value demo. ICT remains the strategic lead.
> Swappable to ICT (or Health) by changing the in-scope services and owner.

## Objective

Validate that Mambo answers citizen questions about Home Affairs services
accurately, safely, and usefully — with measurable success criteria — before
broader rollout.

## Scope

**In scope (services):** national ID replacement, passport application,
birth/death/marriage certificates, citizenship/residence queries — as far as these
are covered by official published documents.

**Out of scope:** case-specific status (requires authenticated systems),
enforcement, payments, anything needing a person's private records.

## Users

- **Primary:** citizens applying for / replacing civil-registration documents.
- **Secondary:** Home Affairs helpdesk / registry counter staff (first-line
  triage), and a departmental reviewer who curates the reviewed-answer cache.

## Duration & phasing

- **Weeks 1–2:** confirm Home Affairs sources + handoff contacts; top up corpus;
  build the sn/nd keyword pilot; re-run eval.
- **Weeks 3–6:** controlled pilot with a named user group (e.g. one registry
  office + a public link with clear "pilot" notice); weekly quality review.
- **Weeks 7–8:** evaluate against success criteria; decide go/no-go for expansion.

## Success criteria

- Route accuracy ≥ 90% on Home Affairs eval questions.
- Citation coverage ≥ 80% on answerable Home Affairs questions.
- Broken-link rate = 0 for cited Home Affairs sources.
- Abstention correctness: 100% on dangerous cases; no fabricated fees/documents.
- p95 latency within target on resourced compute.
- Positive 👍/👎 ratio; qualitative feedback from registry staff.

## Safeguards & escalation

- Every answer shows an evidence-status badge; `unsupported`/`declined` answers
  attach a Home Affairs **handoff card** (office, contact, hours, portal,
  last-verified).
- A human-review owner is named for Home Affairs; the reviewed-answer cache is
  curated for the top ~50 questions.
- Data isolation: pilot uses the official public corpus + minimised query logs;
  no case data, no authentication, no payments.
- Fallback: if retrieval is weak or the model drifts, Mambo falls back to the
  handoff card (not a guess).

## Approval gates

1. Source approval (allow-list + handoff contacts confirmed).
2. Eval pass (criteria above) before public pilot link.
3. Weekly review during pilot; go/no-go at week 8.

## Alignment

Public-value focused, aligned with the National AI Strategy (inclusive, trustworthy
public-service AI) and Home Affairs's mandate (civil registration, secure identity
documents). See `ministry_onboarding_pack.md` for the repeatable onboarding steps.
