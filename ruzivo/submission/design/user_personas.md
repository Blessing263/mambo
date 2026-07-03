# User Personas

Ruzivo serves a whole-of-government audience. Three primary personas drive design.

## 1. Tariro — Citizen (urban, mobile-first)

- **Who:** 28, runs a small business in Harare, Android phone, prepaid data.
- **Needs:** plain-language steps for government tasks (replace a lost ID, register
  a business for tax, get a birth certificate); what to bring; what it costs; where
  to go — without a wasted trip.
- **Frustrations:** fragmented ministry websites, scanned PDFs, jargon, not knowing
  which office handles what.
- **How Ruzivo helps:** service-journey cards (eligibility / what to bring / steps /
  fees / where), citations, mobile-first low-bandwidth, free, day and night.
- **Success:** avoids an unnecessary office visit; arrives with the right documents.

## 2. Sergeant Moyo — Home Affairs helpdesk / registry counter staff

- **Who:** front-line at a registry office; answers the same questions all day.
- **Needs:** fast, accurate, consistent answers to give citizens; a quick way to
  confirm the current procedure/fee; escalate to the right colleague.
- **Frustrations:** outdated printed notices; inconsistent answers between staff.
- **How Ruzivo helps:** a consistent, cited first-line answer; the reviewed-answer
  cache guarantees the top questions are perfect; the handoff card gives the exact
  office/contact when a case needs a human.
- **Success:** faster service; fewer errors; less repeated effort.

## 3. Rumbi — Policy / regulatory analyst (POTRAZ / ministry policy unit)

- **Who:** reviews what citizens ask most; shapes policy and communications.
- **Needs:** see demand (top questions, unanswered questions, missing documents by
  ministry); evidence of where official information is unclear or absent.
- **Frustrations:** no visibility into citizen information needs.
- **How Ruzivo helps:** `query_log` analytics (planned dashboard: top unanswered
  questions, fallback rate, coverage gaps by ministry) turns citizen questions into
  a policy signal.
- **Success:** policy/comms priorities grounded in real citizen demand.

## Secondary personas

- **Journalist** verifying a law/policy with a citable official source.
- **Student** preparing for exams / civic education.
- **SME owner** navigating tax and business registration (overlaps Tariro).

## Design implications

Mobile-first, low-bandwidth, plain language, citations on every claim, honest
evidence-status, and structured whole-problem journeys — all trace directly to
Tariro's and Sergeant Moyo's needs; the analytics persona is served by the
(Phase 2) insights dashboard.
