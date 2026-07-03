# Ministry Handoff Policy

**What:** When Ruzivo cannot answer a question from the official corpus — or the
question is outside its scope — it does not guess. It hands the citizen off to the
right ministry with a structured escalation card. Inspired by Estonia's Bürokratt,
where a public assistant's job includes directing the user to a human/office when
it cannot help.

## When a handoff is shown

A handoff card (`fallback_contact`) is attached whenever the answer's evidence
status is **unsupported** (retrieval below the confidence threshold — no reliable
official source) or **declined** (medical/legal/personal/political/prompt-injection
abstention). The card names the responsible ministry (or ministries) and gives a
real path forward.

## What the card contains

For each responsible ministry, derived from the registry (`registry/ministries.json`,
enriched at load time by `registry/load_registry.py::_handoff_contact`):

- **Ministry** short name
- **Phone / WhatsApp / Email / Address / Office hours** (curated, official)
- **Service portal / counter** link (the ministry's official site)
- **Last verified** date (when the contact was last confirmed against the source)
- **Review owner** (named steward; to be assigned per ministry during onboarding)

## Principles

1. **Never invent contacts.** Every contact field traces to the official registry;
   no contact is generated or guessed. If a field is missing, it is simply absent.
2. **Honest escalation.** The card is shown precisely when Ruzivo cannot stand behind
   an answer — so the citizen always gets a real next step instead of a hallucinated one.
3. **Verifiable recency.** `last_verified_at` tells the citizen (and reviewers) how
   fresh the contact is; stale contacts are flagged for re-verification.
4. **Scoped, not persuasive.** Ruzivo routes; it does not pressure. The card gives
   the office and what to ask, not a recommendation to act.

## Review cadence

- Contacts are re-verified against each source at least **quarterly**, and whenever
  a source's homepage changes.
- `validate_corpus.py` and `check_citation_links.py` flag broken source links; a
  broken source link triggers a contact re-check for that ministry.
- A ministry is not marked `enabled` until its handoff contact is confirmed.

## Relation to abstention

For abstention categories (medical, legal, personal data, political,
prompt-injection) the deferral names the right human/professional path (e.g. a
clinician; the Law Society of Zimbabwe) and, where the registry has the relevant
ministry, attaches that ministry's card. See `rag/guard.py`.
