"""Evaluation harness over the Zimbabwe citizen-query set.

Two modes:
  (default) Router accuracy — deterministic, no LLM. Measures whether router.route()
            returns an expected ministry for each question.
  --full    Full RAG metrics via service.ask() — calls the LLM (slow). Measures
            source-ministry match, citation coverage, fallback rate, latency.
            Use --limit to bound the number of full calls.

Usage:
  uv run python scripts/evaluate_mambo.py                       # router accuracy, all
  uv run python scripts/evaluate_mambo.py --full --limit 10     # + full RAG on 10 Qs
  uv run python scripts/evaluate_mambo.py --out eval.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "eval_questions.jsonl"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_questions() -> list[dict]:
    return [json.loads(line) for line in FIXTURES.read_text().splitlines() if line.strip()]


def router_accuracy(questions: list[dict]) -> list[dict]:
    """Deterministic: router.route() vs expected_ministry. No LLM, no DB writes."""
    from rag import router  # router reads ministries() from the DB (read-only)
    rows = []
    correct = 0
    for q in questions:
        detected = router.route(q["question"])
        expected = set(q.get("expected_ministry", []))
        # answerable questions should route to an expected ministry;
        # abstain questions (expected empty) are scored on abstention separately.
        if expected:
            hit = bool(expected & set(detected))
            correct += hit
            verdict = "correct" if hit else ("weak" if detected else "missed")
        else:
            verdict = "n/a (abstain)"
        rows.append({**q, "detected": detected, "router_verdict": verdict})
    return rows


def full_metrics(questions: list[dict]) -> list[dict]:
    """Slow: calls service.ask() per question (real LLM + retrieval)."""
    from rag import service
    rows = []
    for q in questions:
        t0 = time.time()
        resp = service.ask(q["question"], session_id=f"eval-{q['id']}")
        latency = round((time.time() - t0) * 1000)
        expected = set(q.get("expected_ministry", []))
        src = set(resp.get("source_ministry", []))
        rows.append({
            **q,
            "detected_ministries": resp.get("source_ministry", []),
            "ministry_match": bool(expected & src) if expected else None,
            "confident": resp.get("confident"),
            "citations": len(resp.get("citations", [])),
            "latency_ms": latency,
            "answer_excerpt": (resp.get("answer", "") or "")[:160],
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="also run full RAG metrics (slow)")
    ap.add_argument("--limit", type=int, default=0, help="cap --full questions (0=all)")
    ap.add_argument("--out", default=None, help="write CSV to this path")
    args = ap.parse_args()

    questions = load_questions()
    print(f"Loaded {len(questions)} eval questions "
          f"({sum(1 for q in questions if q['answerable'])} answerable, "
          f"{sum(1 for q in questions if not q['answerable'])} abstain).")

    rrows = router_accuracy(questions)
    answerable = [r for r in rrows if r.get("expected_ministry")]
    correct = sum(1 for r in answerable if r["router_verdict"] == "correct")
    print(f"\nRouter accuracy (deterministic, no LLM): "
          f"{correct}/{len(answerable)} answerable questions routed to an expected ministry "
          f"({round(100*correct/len(answerable),1)}%).")
    for r in rrows:
        print(f"  [{r['router_verdict']:>12}] {r['language']} {r['id']} {r['question'][:50]}")

    out_rows = rrows
    if args.full:
        full_q = questions if not args.limit else questions[: args.limit]
        print(f"\nFull RAG metrics on {len(full_q)} questions (calls LLM)…")
        frows = full_metrics(full_q)
        cited = sum(1 for r in frows if r["answerable"] and r["citations"] > 0)
        ans = [r for r in frows if r["answerable"]]
        fb = sum(1 for r in frows if not r["confident"])
        lat = sorted(r["latency_ms"] for r in frows)
        print(f"  citation coverage (answerable): {cited}/{len(ans)}")
        print(f"  fallback (low-confidence): {fb}/{len(frows)}")
        if lat:
            print(f"  latency ms: min={lat[0]} p50={lat[len(lat)//2]} max={lat[-1]}")
        out_rows = frows

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        fields = sorted({k for r in out_rows for k in r})
        with open(args.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in out_rows:
                w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                            for k, v in r.items()})
        print(f"\nCSV written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
