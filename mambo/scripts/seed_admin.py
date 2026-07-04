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
    {
        "ministry_id": "home_affairs",
        "question": "How do I apply for a passport?",
        "answer": (
            "**Eligibility**\nZimbabwean citizens of any age (minors need a parent/guardian to sign).\n\n"
            "**What to bring**\n- Original long birth certificate + photocopy\n- National ID (driver's licence NOT accepted)\n"
            "- Current or expired passport (if renewing)\n- 2 colour passport photos (3.5cm × 4.5cm, white background, dark clothes)\n"
            "- Marriage certificate (if surname changed)\n- Police report (if lost/stolen)\n\n"
            "**Steps**\n1. Complete the application form at the Passport Office.\n2. Book a biometric capture appointment.\n"
            "3. Attend in person for biometrics (fingerprints, photo).\n4. Pay the applicable fee.\n\n"
            "**Fees**\nOrdinary: US$50 | Urgent (3 working days): US$250 | Executive (1 day): US$315\n\n"
            "**Where to apply**\nThe Passport Office (Harare/Bulawayo) or any Zimbabwe embassy/consulate abroad."
        ),
        "citations": [
            {"title": "Embassy of Zimbabwe to the USA — Passport Information", "url": "https://zimembassydc.org/passport-information/", "ministry": "home_affairs"},
            {"title": "Zimbabwe Embassy Lusaka — Passport Application", "url": "http://www.zimlusaka.gov.zw/passport-application/", "ministry": "home_affairs"},
        ],
    },
    {
        "ministry_id": "zimra",
        "question": "How do I get a tax clearance certificate?",
        "answer": (
            "**Eligibility**\nYou must be a registered taxpayer with ZIMRA (registered under Section 42 of the Income Tax Act) "
            "and be fully tax-compliant — all returns filed, all taxes paid.\n\n"
            "**What you need**\n- A valid Taxpayer Identification Number (TIN/BPN)\n- All tax returns up to date\n- No outstanding tax debts\n\n"
            "**Steps**\n1. Ensure you are registered with ZIMRA and have a Business Partner Number (BPN).\n"
            "2. File all outstanding returns and pay any amounts due.\n"
            "3. The Tax Clearance Certificate (ITF263) is **auto-generated** by the ZIMRA TaRMS system "
            "for compliant taxpayers — no manual application is needed.\n"
            "4. It is sent to the email address ZIMRA has on record for your business.\n\n"
            "**Fees**\nNo fee — the certificate is issued free to compliant taxpayers.\n\n"
            "**Where to apply**\nOnline via the ZIMRA TaRMS portal, or visit any ZIMRA office for assistance."
        ),
        "citations": [
            {"title": "ZIMRA — Tax Clearance Certificate (ITF263)", "url": "https://www.zimra.co.zw/news/2235:tax-clearance-certificate-itf263-2", "ministry": "zimra"},
        ],
    },
    {
        "ministry_id": "home_affairs",
        "question": "How do I register a birth certificate?",
        "answer": (
            "**Eligibility**\nAny child born in Zimbabwe to Zimbabwean parents, or children of Zimbabwean citizens born abroad. "
            "Registration should be done as soon as possible after birth (within 42 days).\n\n"
            "**What to bring**\n- Completed Birth Registration form (BD3)\n- Child's birth record from the hospital or clinic\n"
            "- Both parents' national identity cards\n- Parents' marriage certificate (if applicable)\n- One witness with a valid national ID\n\n"
            "**Steps**\n1. Obtain the birth record from the hospital/clinic where the child was born.\n"
            "2. Complete the BD3 registration form.\n3. Bring all documents to the Civil Registry office.\n"
            "4. The birth certificate is typically issued on the same day.\n\n"
            "**Fees**\nFirst registration is free. Late registration may attract a fee.\n\n"
            "**Where to apply**\nAny Civil Registry office or the Registrar General's office."
        ),
        "citations": [
            {"title": "Embassy of Zimbabwe to the USA — Notice of Birth", "url": "https://zimembassydc.org/notice-of-birth/", "ministry": "home_affairs"},
            {"title": "Ministry of Home Affairs and Cultural Heritage", "url": "https://www.moha.gov.zw/en/", "ministry": "home_affairs"},
        ],
    },
    {
        "ministry_id": "zimsec",
        "question": "How do I check exam results or replace a certificate?",
        "answer": (
            "**Eligibility**\nAny candidate who has written ZIMSEC examinations (Grade 7, O-Level, or A-Level).\n\n"
            "**Important:** ZIMSEC does **NOT** issue duplicate certificates. Instead, they provide a **Certifying Statement of Results** "
            "which serves as official confirmation of your examination results.\n\n"
            "**What to bring**\n- Completed Confirmation of Results form (available on the ZIMSEC website or at any ZIMSEC office)\n"
            "- Your original examination details (centre number, candidate number, year sat, subjects)\n- A valid national ID\n- Fee payment\n\n"
            "**Steps**\n1. Complete the Confirmation of Results form (ZGCE Certifying Statement).\n"
            "2. Apply online at www.zimsec.co.zw or in person at your nearest ZIMSEC regional office.\n3. Pay the applicable fee.\n"
            "4. The Certifying Statement is sent directly to the requesting authority (institution/employer), not handed to the candidate.\n\n"
            "**Fees**\nA fee applies; confirm the current amount at the ZIMSEC office or website.\n\n"
            "**Where to apply**\nZIMSEC regional offices nationwide or online at www.zimsec.co.zw."
        ),
        "citations": [
            {"title": "ZIMSEC — Confirmation of Results", "url": "https://www5.zimsec.co.zw/wp-content/uploads/2025/04/CONFIRMATION-OF-RESULTS2.docx", "ministry": "zimsec"},
            {"title": "ZIMSEC — Examination Administration", "url": "https://www5.zimsec.co.zw/examinations-administration/", "ministry": "zimsec"},
        ],
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
