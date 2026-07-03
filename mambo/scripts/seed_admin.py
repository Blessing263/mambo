"""Seed ministry demo-staff accounts + sample curated (reviewed) answers.

Idempotent. The demo password is env-overridable (MAMBO_ADMIN_PASSWORD, default
'mambo2026'). The sample curated answers use the EXACT journey-tile question
strings, so those tiles return the vetted answer instantly in the demo.

Run:  uv run python scripts/seed_admin.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.db import get_conn  # noqa: E402
from rag.auth import hash_password, normalize_question  # noqa: E402

PASSWORD = os.environ.get("MAMBO_ADMIN_PASSWORD", "mambo2026")
REGISTRY = json.loads(
    (Path(__file__).resolve().parent.parent / "registry" / "ministries.json").read_text()
)

SAMPLE_REVIEWED = [
    {
        "ministry_id": "home_affairs",
        "question": "How do I replace a lost national ID?",
        "answer": (
            "**Eligibility**\nAny Zimbabwean citizen whose national identity card has been lost, stolen, or damaged.\n\n"
            "**What to bring**\n- Original (long) birth certificate\n- A copy of the lost ID (if available)\n"
            "- A police report or affidavit confirming the loss\n- The replacement fee receipt\n\n"
            "**Steps**\n1. Report the loss at your nearest police station and obtain a report.\n"
            "2. Go to the Civil Registry / Registrar General's office with your documents.\n"
            "3. Submit the application and pay the fee.\n"
            "4. You will be issued a temporary waiting card while the replacement is processed.\n\n"
            "**Fees**\nThe replacement fee is set by the Civil Registry; confirm the current amount at the office.\n\n"
            "**Where to apply**\nAny Civil Registry office or the Registrar General (Makombe Building, Harare)."
        ),
        "citations": [{"title": "Ministry of Home Affairs and Cultural Heritage", "url": "https://www.moha.gov.zw/en/", "ministry": "home_affairs"}],
    },
    {
        "ministry_id": "ict",
        "question": "What is the National AI Strategy?",
        "answer": (
            "The **National AI Strategy** is Zimbabwe's framework for turning artificial intelligence into "
            "practical, inclusive public value. Launched in March 2026, it is implemented through programmes "
            "like the AI for Impact Challenge (AI4I). It prioritises public-service delivery, local AI "
            "capability, digital sovereignty, and responsible AI governance. The Ministry of ICT leads it; "
            "read the full strategy on the Ministry of ICT website."
        ),
        "citations": [{"title": "Ministry of ICT, Postal & Courier Services", "url": "https://www.ictministry.gov.zw/", "ministry": "ict"}],
    },
]


def main() -> None:
    pw_hash = hash_password(PASSWORD)
    with get_conn() as conn, conn.cursor() as cur:
        # demo staff per enabled ministry
        for m in REGISTRY["ministries"]:
            if not m.get("enabled", True):
                continue
            email = f"{m['id']}@demo.mambo"
            cur.execute(
                """INSERT INTO staff (ministry_id, email, name, role, password_hash)
                   VALUES (%s, %s, %s, 'agent', %s)
                   ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash,
                                                     name = EXCLUDED.name;""",
                (m["id"], email, f"{m['short_name']} Demo Agent", pw_hash),
            )
        # sample curated answers (idempotent: delete by (ministry, question_norm) then insert)
        for r in SAMPLE_REVIEWED:
            qn = normalize_question(r["question"])
            cur.execute(
                "DELETE FROM reviewed_answers WHERE ministry_id = %s AND question_norm = %s;",
                (r["ministry_id"], qn),
            )
            cur.execute(
                """INSERT INTO reviewed_answers (ministry_id, question, question_norm, answer, citations, enabled)
                   VALUES (%s, %s, %s, %s, %s, true);""",
                (r["ministry_id"], r["question"], qn, r["answer"], json.dumps(r["citations"])),
            )
        conn.commit()
        cur.execute("SELECT email, ministry_id FROM staff ORDER BY ministry_id;")
        rows = cur.fetchall()
    print(f"Seeded {len(rows)} demo staff (password: {PASSWORD}):")
    for r in rows:
        print(f"  {r['email']:36} -> {r['ministry_id']}")
    print(f"+ {len(SAMPLE_REVIEWED)} sample curated answers (home_affairs/lost-ID, ict/AI-Strategy).")


if __name__ == "__main__":
    main()
