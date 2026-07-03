# Service Journeys

**What:** For the most common citizen tasks, Mambo answers as a structured
**whole-problem card** — not a generic paragraph. Each card covers the *whole*
task (eligibility, what to bring, steps, fees, where to apply, timeline), grounded
in official documents and cited throughout. Inspired by GOV.UK service design:
start with the user need and solve the whole problem, not just answer a fragment.

## How it works

- `registry/journeys.json` defines the journeys (id, title, ministry, match
  keywords, card sections).
- `rag/journeys.py::match_journey(question)` picks the best-matching journey by
  whole-word keyword hits (returns `None` when nothing matches → normal RAG answer).
- When a journey matches, `rag/prompt.py::journey_directive(journey)` appends
  instructions that shape the grounded RAG answer under the card's bold headings.
- No new UI is required: the model emits the card as markdown (`**Eligibility**`,
  bullet lists, `[n]` citations) which the existing `AnswerText` renderer already
  presents cleanly.

## Initial journeys (6)

| Journey | Ministry | Trigger examples |
|---|---|---|
| Replacing a lost national ID | Home Affairs | "lost id", "replace national id" |
| Applying for a passport | Home Affairs | "passport", "renew passport" |
| Getting a tax clearance certificate | ZIMRA | "tax clearance certificate" |
| Registering a birth certificate | Home Affairs | "birth certificate", "register a birth" |
| Registering a business for tax | ZIMRA | "register a business", "taxpayer registration" |
| Exam results / certificate replacement | ZIMSEC | "exam results", "lost zimsec certificate" |

## Honest per-section behaviour (responsible-AI)

Every card section is grounded and cited. If the official documents do not cover a
section, the model writes *"Not specified in the official documents I hold"* for
that section — it never guesses fees, documents, or timelines. This pairs directly
with the **evidence-status** badge and the **ministry handoff** card: a partial card
still gives the citizen the parts that are grounded plus a real office to contact
for the rest.

## Evaluation

The router-accuracy eval already covers several journey triggers (lost ID, passport,
tax clearance, birth certificate). Journey shaping is verified by unit tests
(`tests/test_journeys.py`); end-to-end card quality is part of the full RAG
evaluation run (`scripts/evaluate_mambo.py --full`).

## Extending

Add a journey by appending to `registry/journeys.json` (id, title, ministry,
keywords, sections) and reloading the registry. No code change is needed for new
journeys that reuse the standard section set.
