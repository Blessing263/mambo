# Mambo — Foundation Spec

> **Mambo** (Shona: *"knowledge"*) — a plain-language, citizen-facing information
> assistant for the Government of Zimbabwe. Ask a question in everyday words; get a
> clear, correct answer drawn **only** from official ministry documents, with the
> source always shown.

This document is the **single source of truth** for the project. Architecture,
scope, decisions, and the build plan all live here. If anything elsewhere conflicts
with this file, this file wins until it is deliberately updated.

---

## 1. Vision

Not one ministry's chatbot — a **whole-of-government** assistant. The Ministry of
ICT leads (it is the ministry we pitch to), but the platform is designed so **every
ministry plugs in**. A citizen can ask anything and Mambo routes them to the right
ministry, answers from that ministry's official documents, and names the source.

The name scales: *Mambo* = "knowledge," not "ICT knowledge."

**Pitch framing:** ICT doesn't just build a tool for itself — it builds the thing
that helps Health, Home Affairs, and every other ministry serve citizens. Leadership
made visible.

---

## 2. Core principles (these constrain every decision)

1. **Trust first.** A *wrong* answer is worse than *no* answer. Mambo answers only
   from official documents, always cites the source, and says "I don't know, here's
   who to contact" when the documents don't cover something.
2. **Only official sources in → only official answers out.** The system never
   touches the open internet at answer time and only ever ingests official
   `*.gov.zw` domains (enforced by the Ministry Registry allow-list, §6).
3. **One brain, two faces.** The chat UI is built once and delivered two ways:
   a standalone demo page now, an embeddable website widget later. Same code.
4. **Modular, swappable boxes.** Three modules meet at clean seams. Any one box can
   be upgraded without touching the others.
5. **Sovereignty path.** Start on cheap hosted infrastructure for the demo; design
   so Phase 2 can run entirely on Ministry-owned servers (self-hosted model + DB).
6. **The demo and the national system are the same system.** Phase 2 is *additions
   and swaps* to these boxes — never a rewrite.

---

## 3. Architecture — three modules + a shared Knowledge Store

```
  MODULE 3 (Ingestion)              KNOWLEDGE STORE            MODULE 2 (RAG)            MODULE 1 (Webchat)
  scrape · discover · parse         ┌──────────────┐
  · chunk · embed         ──writes──▶│  Postgres +  │◀──reads── retrieve · route ·   ◀─API─ the chat UI
                                     │   pgvector   │           augment · generate ·         (the face)
                                     │  (tagged by  │           trust layer
                                     │   ministry)  │ ──────────▶
                                     └──────────────┘
        runs OCCASIONALLY                                       runs PER QUESTION       runs IN THE BROWSER
        (batch job, not a service)                              (always-on service)     (always-on, cheap)
```

**Why split this way:** each module runs on a different *rhythm* — ingestion
occasionally, RAG per question, webchat constantly. Splitting by rhythm lets each
scale and run independently.

### The two boundaries
- **Webchat ↔ RAG = an API** (question in → answer + citations out). This boundary
  is what gives us "one brain, two faces" — the same RAG backend serves both the
  standalone demo and the future widget.
- **RAG ↔ Ingestion = the database** (no live connection; they only share the
  Knowledge Store). Ingestion's job is to *fill it correctly*; RAG's job is to
  *read it well*.

### The Knowledge Store (the seam)
Postgres + `pgvector`. Same technology runs on a cheap cloud box (demo) **and** on a
Ministry server (Phase 2) — one technology, two homes, no migration drama. Every
chunk is **tagged by ministry** from day one (required for routing).

---

## 4. Module 1 — Webchat (the face)

**Tech:** Next.js + **assistant-ui** (chat components we *copy in and own* — not a
forked platform). Backend-agnostic: it only calls our RAG API. MIT-licensed so the
Ministry can freely own and modify it. Mobile-first (most citizens are on phones).

**Delivery:** standalone branded page for the demo → same React app wrapped as an
embeddable `<script>` widget for the Ministry website in Phase 2.

### Feature set
Tags: **[Demo]** build now · **[P2]** Phase 2 · **[Future]** later.

**Conversation (core):**
- Plain-language Q&A **[Demo]**
- Streaming answers (types out live) **[Demo]**
- **Citation / source cards** — clickable "Source: National AI Strategy, p.12 →" **[Demo]**
- Honest fallback → Ministry contact line **[Demo]**
- Session memory (understands "what about *rural* areas?") **[Demo]**
- Suggested follow-up chips **[Demo]**
- Copy / share answer (incl. WhatsApp) **[Demo]**

**Multi-ministry:**
- **Ministry picker** — cards; 3–4 ministries live in the demo **[Demo]**
- **"Find the right office" router** — describe a problem → routed to the exact
  ministry + department + form. *Flagship demo feature.* **[Demo]**
- Smart contact/directory tool (phone, WhatsApp, address, hours, map) **[Demo: ICT]**
- "All of Government" free-ask mode **[P2]**
- Per-ministry theming **[P2]**

**Getting started:**
- Starter question chips on empty state **[Demo]**
- Browse by topic **[Demo]**
- Popular questions **[P2]**

**Language & accessibility:**
- Mobile-first + low-bandwidth mode **[Demo]**
- Basic large-text / high-contrast (WCAG) **[Demo]**
- Language switch: English / Shona / Ndebele **[P2]**
- Voice input + read-aloud answers **[P2]**

**Feedback & trust signals:**
- 👍/👎 per answer **[Demo]**
- "Sources last updated" date **[Demo]**
- Scope indicator (answer is from official docs) **[Demo]**
- "Report this answer" **[P2]**

**Interactive tools (beyond Q&A):**
- "Find the right office" router — **[Demo]** (see above)
- Guided wizards / checklists **[P2]**
- Eligibility checker **[P2]**
- One-page summary generator **[P2]**
- Glossary / "explain this term" **[P2]**
- Submit an idea / feedback to a ministry **[P2]**
- Service deep-links to existing e-gov portals **[P2]**
- Civic-education quizzes **[Future]**

---

## 5. Module 2 — RAG (the brain + trust layer)

The query path, per question:

```
  question
     ↓
  1. ROUTE      ← which ministry/ministries does this belong to? (the "traffic cop")
     ↓
  2. RETRIEVE   ← embed the question, search the Knowledge Store (scoped to those ministries)
     ↓
  3. AUGMENT    ← hand ONLY the retrieved official chunks to the model
     ↓
  4. GENERATE   ← DeepSeek writes a plain-language answer from those chunks
     ↓
  5. TRUST LAYER← enforce citations, confidence threshold, topic-lock, fallback
     ↓
  answer + citations + source ministry
```

### Models
- **Generation (the backbone):** **DeepSeek V4 Pro**, via DeepSeek's hosted API for
  the demo. Sits behind a **swappable model interface** — Phase 2 can swap in a
  self-hosted open-weight model (DeepSeek or other) on Ministry servers with no
  change to Modules 1 or 3.
- **Embeddings (for search):** a **multilingual, open-source, self-hostable**
  embedding model. Separate job from generation. Multilingual *from day one* so
  Shona/Ndebele in Phase 2 is an addition, not a re-embed of everything.

### The router ("traffic cop")
Before retrieval, classify the question to one or more ministries (using the
Registry mandates, §6), then retrieve only within those ministries' documents, and
name the source ministry in the answer. This powers "Find the right office."

### Trust layer rules (enforced here, NOT in the webchat)
- **Mandatory citations** on every answer.
- **Confidence threshold:** if retrieval doesn't clearly cover the question, do not
  guess — say so and route to the Ministry's contact line.
- **Topic-lock:** politely refuse anything outside government/ministry scope.
- **Reviewed-answer cache (P2):** humans vet the top ~50 questions per ministry so
  the most-seen answers are guaranteed perfect.
- **Question log:** every question recorded → feeds the Phase-2 analytics ("what
  citizens ask most") and quality review. (Public questions only; no private data.)

---

## 6. The Ministry Registry — the keystone

A small, curated, **verified** structured file. One artifact powers five things:

1. **Seeds the scraper** — tells discovery which sites to crawl.
2. **Security allow-list** — Mambo only ever crawls/cites official `*.gov.zw`
   domains. The trust boundary for ingestion.
3. **Tags every chunk** with its ministry (powers routing).
4. **Powers the ministry picker** UI.
5. **Powers "Find the right office"** + the contact tool.

### Registry entry shape (per ministry)
```
- id:            "ict"
  name:          "Ministry of Information Communication Technology, Postal & Courier Services"
  mandate:       "ICT policy, telecoms, postal services, data protection, digital economy…"
  keywords:      ["internet", "data protection", "broadband", "AI", "cyber", …]   # routing hints
  domains:       [" ict.gov.zw ", …]      # allow-list — scraper scope
  doc_pages:     ["…/policies", "…/downloads", …]   # known publication pages
  contact:
    phone:       "…"
    whatsapp:    "…"
    address:     "76 Samora Machel Avenue, Harare"
    hours:       "…"
```

**Source of truth:** we curate it ourselves, verified against each official site
(seeded from the national e-gov portal where a list exists). ~20 ministries, curated
once, maintained as needed.

---

## 7. Module 3 — Ingestion (proper data pipeline)

```
1. REGISTRY (seed)      ← official domains only (allow-list)
2. DISCOVER / CRAWL     ← walk each official site; detect NEW/CHANGED docs
                          (polite: robots.txt, rate-limited, allow-list only)
3. FETCH                ← download PDFs/HTML; keep RAW original (provenance)
4. EXTRACT / PARSE      ← clean text + metadata (title, ministry, URL, page#, date)
                          ⚠ OCR fallback for SCANNED PDFs
5. CHUNK                ← search-sized pieces, keeping page/section refs (for citations)
6. EMBED                ← multilingual embedder → vectors
7. LOAD                 ← chunks + vectors + metadata → Knowledge Store, tagged by ministry
8. TRACK / REFRESH      ← content hashes → only re-process changed docs next run
```

### What makes it "proper" (non-negotiable)
- **OCR fallback** — many government PDFs are scanned images; without OCR they're invisible.
- **Incremental refresh** — re-runs touch only new/changed docs ("kept current automatically").
- **Provenance** — every chunk stores exact source URL + page + fetch date, so every
  citation is verifiable.
- **Politeness & allow-list** — only official domains, rate-limited, robots-respecting.
  Mambo must never look like it's attacking government servers.

**Runs as a scheduled batch job, not an always-on service** (cost control).

---

## 8. Data contracts (the shapes that cross the seams)

### A chunk in the Knowledge Store
```
chunk:
  id:            uuid
  ministry_id:   "ict"                      # tag for routing/scoping
  document_id:   uuid
  text:          "…the official passage…"
  embedding:     <vector>
  source_url:    "https://ict.gov.zw/…/ai-strategy.pdf"
  source_title:  "National AI Strategy"
  page:          12
  fetched_at:    "2026-06-07"
  content_hash:  "…"                         # for incremental refresh / dedupe
```

### Webchat → RAG (request)
```
{ "question": "...", "session_id": "...", "ministry_filter": null }   # null = let the router decide
```

### RAG → Webchat (response)
```
{
  "answer": "plain-language answer…",
  "source_ministry": ["ict"],
  "citations": [
    { "title": "National AI Strategy", "page": 12, "url": "https://ict.gov.zw/…" }
  ],
  "confident": true,                     # false → UI shows fallback + contact
  "fallback_contact": null
}
```

---

## 9. Tech stack summary

| Layer | Choice | Notes |
|---|---|---|
| Webchat | Next.js + assistant-ui | Components we own; MIT; mobile-first |
| RAG API | Small backend service | Hosts route→retrieve→augment→generate→trust |
| Generation LLM | **DeepSeek V4 Pro** (API) | Behind swappable interface; self-host in P2 |
| Embeddings | Multilingual open-source, self-hosted | Future-proofs Shona/Ndebele |
| Knowledge Store | Postgres + pgvector | Cloud for demo → Ministry server for P2 |
| Ingestion | Batch pipeline (scheduled) | Scrape/discover/parse/OCR/chunk/embed/load |
| Repo | Monorepo, one repo / four folders | Easy Ministry handover |

---

## 10. Repo structure

```
mambo/
├── webchat/      ← Module 1 (the face)
├── rag/          ← Module 2 (the brain + trust layer + model interface)
├── ingestion/    ← Module 3 (scrape · discover · parse · chunk · embed)
├── registry/     ← the Ministry Registry (source of truth + allow-list)
├── shared/       ← types/contracts both sides agree on
└── FOUNDATION.md ← this file
```

---

## 11. Phased plan

### Phase 1 — Demo (now, minimal cost)
- 3–4 ministries **actually live** with real scraped documents.
- Webchat **[Demo]** features (above), standalone branded page.
- RAG: route → retrieve → DeepSeek → trust layer, with citations.
- Ingestion: full proper pipeline, run to seed the 3–4 ministries.
- Hosting: one cheap cloud instance + hosted Postgres.
- Goal: a real national-feeling service to show the Minister on a link.

### Phase 2 — Full initiative (funded, Ministry-owned)
- All ~20 ministries.
- Swap LLM to Ministry-hosted open-weight model; move Postgres to Ministry servers.
- Shona / Ndebele (translation step in RAG; embeddings already multilingual).
- Admin panel (staff upload docs → triggers ingestion; no developer needed).
- Analytics dashboard + reviewed-answer cache.
- Embeddable widget on the live Ministry website.
- Remaining interactive tools (wizards, eligibility, summaries, etc.).

---

## 12. Open questions / to verify

- **DeepSeek V4 Pro specifics:** confirm open-weight availability (for P2 self-host),
  context-window size, and pricing (to size chunks + estimate cost).
- **Embedder choice:** pick the specific multilingual open-source model.
- **Ministries for the demo:** ICT (lead) + Health + Home Affairs confirmed as the
  high-traffic set; **the 4th (Finance or Education) is TBD.**
- **Ministry website platform:** for the Phase-2 widget embed (WordPress?).
- **Hosting for the demo:** cloud provider + region.
```
