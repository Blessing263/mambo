"""Service Journey Mode — matcher + prompt directive."""

from __future__ import annotations

from rag import journeys
from rag.prompt import journey_directive


def test_match_lost_id():
    j = journeys.match_journey("How do I replace a lost national ID?")
    assert j and j["id"] == "lost_national_id"


def test_match_passport():
    j = journeys.match_journey("What do I need to apply for a passport?")
    assert j and j["id"] == "passport"


def test_match_tax_clearance():
    j = journeys.match_journey("How do I get a tax clearance certificate?")
    assert j and j["id"] == "tax_clearance"


def test_match_birth_certificate():
    j = journeys.match_journey("How do I register a birth certificate for a newborn?")
    assert j and j["id"] == "birth_certificate"


def test_no_match_for_general_question():
    assert journeys.match_journey("What is the National AI Strategy?") is None


def test_journey_directive_lists_sections():
    j = journeys.match_journey("replace my lost id")
    d = journey_directive(j)
    assert "Service card" in d and "**Steps**" in d and "**Fees**" in d


def test_all_journeys_well_formed():
    for j in journeys.all_journeys():
        assert j["id"] and j["title"] and j["ministry"] and j["sections"] and j["keywords"]
