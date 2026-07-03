"""Safety guard — abstain from categories Ruzivo must not answer, and route the
user to a real human/professional path instead.

Scope: official Zimbabwe government information only. Ruzivo must NOT give medical
diagnoses, legal conclusions, personal-data lookups, political opinions, or obey
prompt-injection. These get a short, honest deferral plus the right referral.

Runs BEFORE retrieval and intent classification, so abstention is deterministic and
LLM-free (fast, testable, and impossible for the model to talk its way around).
"""

from __future__ import annotations

import re

# category -> (referral ministry ids, compiled regex)
_RULES: list[tuple[str, list[str] | None, re.Pattern]] = [
    ("prompt_injection", None, re.compile(
        r"(?i)(ignore (your |the |previous |prior |all )?(previous |prior )?instructions"
        r"|disregard (the |your |above )?(previous |prior )?(instructions|rules)"
        r"|print (out )?(me )?the system (prompt|instructions)"
        r"|reveal (your |the )?(system prompt|instructions|rules)"
        r"|you are (now )?(DAN|jailbroken|in (developer|root) mode)"
        r"|act as (if )?(a |an )?(different |new )?(ai|assistant)( without rules)?\b)")),
    ("medical_advice", ["health"], re.compile(
        r"(?i)(\bdiagnos\w*|what (medicine|drug|tablet|pill)s? should i take"
        r"|which (medicine|drug) (should i |to )?(take|for)|medication (for|to take)"
        r"|\bprescrib\w*|my symptoms?|i have (a )?(fever|chest pain|pain|cough|rash|sore)"
        r"|dosage (of|for)|am i (sick|pregnant|infected)|do i have\b"
        r"|how do i treat (my|this)|treat my\b)")),
    ("legal_advice", ["veritas", "zimlii"], re.compile(
        r"(?i)(can i sue|whether i can sue|can (he|she|they|i) (sue|be sued)"
        r"|(sue|suing) (him|her|them|my|the|someone)|\bsuing\b"
        r"|file (a |an )?(lawsuit|suit|case)|take (legal )?action|legal action"
        r"|should i (sign|file|sue|settle|take)|is it (legal|illegal)"
        r"|legal (advice|conclusion|opinion|representation)"
        r"|what is my liabilit|will i win|represent me (in |at )?(court|my case)"
        r"|advise me (on|whether|if)|do i have a (case|claim|lawsuit))")),
    ("personal_data", None, re.compile(
        r"(?i)((home |physical |email )?address|phone number|mobile number|id number"
        r"|national id|contact details|where (does|do) .{3,40} (live|work|stay)"
        r"|(find|look up|get|give me|what is) .{0,30}(address|phone number|contact)"
        r"|(locate|track) (a |an |the )?(person|someone|individual))")),
    ("political", None, re.compile(
        r"(?i)(who (should i|i )vote for|which (political )?party (should i )?(vote for|is best)"
        r"|best political party|vote (for|against) .{0,30}party"
        r"|(endorse|support) .{0,20}(zanu|mdc|party|candidate)|political opinion"
        r"|which (candidate|party) should)")),
]

DEFER_TEXT: dict[str, str] = {
    "prompt_injection":
        "I can only help with official Zimbabwe government information. I can't "
        "ignore my instructions or reveal how I work.",
    "medical_advice":
        "I can share official public-health information (like immunisation schedules), "
        "but I can't diagnose symptoms or recommend treatment. Please speak to a "
        "clinician, or your nearest clinic or hospital, for anything medical.",
    "legal_advice":
        "I can point you to public Acts, Statutory Instruments and judgments, but I "
        "can't give legal advice or tell you whether to take legal action. Please "
        "consult a registered legal practitioner (Law Society of Zimbabwe) or a "
        "legal-aid clinic.",
    "personal_data":
        "I can't look up or share people's personal details. For official records "
        "about yourself, contact the relevant ministry or office directly.",
    "political":
        "I don't express political opinions or endorse parties or candidates. I stick "
        "to official, factual government information.",
}


def detect_unsafe(question: str) -> tuple[str, list[str] | None] | None:
    """Return (category, referral_ministry_ids) if the question is out-of-scope/unsafe."""
    for category, ministries, rx in _RULES:
        if rx.search(question):
            return category, ministries
    return None
