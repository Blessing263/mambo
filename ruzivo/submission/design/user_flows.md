# User Flows

## 1. Ask a question (core)

1. Land on the prompt (starter chips + ministry focus picker).
2. Type a question (or tap a starter chip) → Enter.
3. See "searching official documents…" → answer streams in with inline `[n]` citations.
4. Answer footer shows the **evidence-status badge** (answered / partial /
   unsupported / declined).
5. Tap a citation card → opens the official source (PDF/HTML) at the right page.
6. 👍/👎 feedback; copy/share the answer.

## 2. Follow a service journey

1. Ask a journey question (e.g. "how do I replace a lost national ID?").
2. Ruzivo returns a **structured card**: Eligibility, What to bring, Steps, Fees,
   Where to apply, Expected timeline — each grounded + cited; "Not specified in the
   official documents I hold" where the corpus is silent.
3. Citizen arrives at the office with the right documents, or taps the service
   portal link.

## 3. Get a handoff (unsupported / declined)

1. Ask something the corpus doesn't cover (or an out-of-scope/unsafe question).
2. Ruzivo shows an honest status (unsupported / declined) **and a handoff card**:
   responsible ministry, phone/WhatsApp/email/address/hours, service portal,
   last-verified date.
3. For abstention categories, the deferral names the right human path (clinician,
   Law Society, the relevant ministry).

## 4. Follow up conversationally

1. Ask a follow-up ("what about for schools?").
2. Ruzivo resolves the reference against recent turns (query rewrite) and answers
   in the new context.

## 5. Focus on a ministry

1. Pick a ministry in the sidebar/focus picker.
2. Subsequent questions retrieve scoped to that ministry's documents; the answer
   badges the responsible ministry.

## 6. Give feedback (quality signal)

1. 👍/👎 on any answer → feeds the monitoring/quality loop and (Phase 2) the
   reviewed-answer cache curation.

## Failure / edge flows

- **Service unreachable:** friendly error; user can retry.
- **Nonce/expiry:** frontend auto-refreshes the security token and retries once.
- **Off-topic / unsafe:** topic-lock or abstention guard responds honestly with a
  redirect, never a guess.
