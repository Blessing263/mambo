# Sustainability & Future Adoption

## Operating model

Ruzivo is open-source and self-hostable by design (open-weight embeddings, a
swappable generation interface, Postgres+pgvector that runs on a cheap cloud box
**or** a Ministry server). The cost model shows infrastructure is inexpensive; the
real ongoing cost is **people**: a reviewer per ministry batch to curate the
reviewed-answer cache, and part-time engineering for re-crawls and eval re-runs.

## Adoption pathway

1. **Pilot** with one ministry (Home Affairs proposed — see `pilot_blueprint.md`),
   grant-backed by AI4I milestone support, with a named review owner.
2. **Per-ministry onboarding** via `ministry_onboarding_pack.md` — repeatable,
   ministry staff do most of it without developer help.
3. **Whole-of-government** rollout: each ministry plugs into the same platform
   (the registry is the keystone); the reviewed-answer cache grows per ministry.
4. **Embeddable widget** on live ministry websites + low-bandwidth channels
   (WhatsApp first) for reach.

## Funding / revenue

- **Near term:** milestone-based AI4I support + a ministry-hosted pilot
  (public-value, not commercial).
- **Medium term:** ministry onboarding/support fees; the platform as shared
  digital-public-infrastructure across government (cost-shared).
- **Open-source path** keeps exit costs low and avoids vendor lock-in — a Ministry
  can run the whole stack on its own servers (self-hosted model + DB) with no
  per-query API cost, especially once on the ZCHPC CCE.

## Maintenance & review workflow

- **Incremental refresh** re-ingests only changed documents (content_hash).
- **Quarterly** contact + source re-verification; eval re-run after material
  corpus changes.
- **Reviewed-answer cache** for the top ~50 questions per ministry → guaranteed-
  perfect answers for the most-seen queries + a rule-baseline fallback if
  generation degrades.
- **Monitoring** (see `monitoring_plan.md`) drives what to fix next.

## Risks to sustainability (and handling)

- **Staff dependence:** mitigate with the repeatable onboarding pack + reviewed-
  answer cache (lowers the per-ministry effort over time).
- **Model cost/lock-in:** mitigate with the swappable interface + CCE self-host.
- **Source churn:** mitigate with incremental refresh + broken-link checks.
- **Overreach:** mitigate by staying scoped (information + routing + handoff), not
  building authenticated case-management.

## Honesty

Ruzivo is positioned as a **guidance and routing assistant**, not a replacement for
official decisions, professional advice, or ministry confirmation. That scope
discipline is itself a sustainability feature: it bounds the maintenance surface
and the liability surface.
