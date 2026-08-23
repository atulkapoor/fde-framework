"""Free-flow prose into facts.

Deterministic: registry vocabulary plus quantity patterns, no model. That keeps
intake replayable and keeps it working inside an air gap. An LLM-assisted parser
is a later realization behind this same signature.

The bar is not "extracts a lot". It is "extracts only what is actually there".
A parser that guesses is worse than one that returns nothing, because a wrong
fact with ARTIFACT provenance outranks the interview that would have corrected it.
"""

from pathlib import Path

import pytest

from fde.intake.prose import parse_prose, restate
from fde.models.base import Provenance
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"

DOC_EXTRACTION = (
    "Extract financial fields from unstructured invoice PDFs into a unified JSON "
    "schema. Layouts vary across institutions. 200,000 documents, 8,000 verified. "
    "Data cannot leave the client environment."
)
STUDIO = (
    "Generate promotional imagery in our house style from unreleased IP. "
    "The environment is air-gapped. Nobody is waiting on the result."
)
ROUTE = (
    "Schedule 400 vehicles against hard capacity and time-window constraints. "
    "Responses must return in under 200ms."
)
CHURN = (
    "Predict which of 2 million accounts will churn next quarter. The model must "
    "be explainable to the regulator."
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def dims(facts):
    return {f.dimension: f.value for f in facts}


# --- quantities ----------------------------------------------------------


def test_counts_are_read_with_their_unit(reg):
    assert dims(parse_prose(DOC_EXTRACTION, reg))["corpus_size"] == 200_000


def test_a_second_count_with_a_different_unit_is_a_different_dimension(reg):
    """200,000 documents and 8,000 verified are not the same measurement."""
    d = dims(parse_prose(DOC_EXTRACTION, reg))
    assert d["corpus_size"] == 200_000
    assert d["labelled_count"] == 8_000


def test_written_scale_words_are_understood(reg):
    assert dims(parse_prose(CHURN, reg))["corpus_size"] == 2_000_000


def test_durations_are_normalised_to_milliseconds(reg):
    assert dims(parse_prose(ROUTE, reg))["latency_budget_ms"] == 200


def test_a_bare_number_with_no_recognisable_unit_is_not_guessed(reg):
    """Guessing produces a wrong fact at artifact strength, which then outranks
    the interview answer that would have corrected it."""
    assert parse_prose("There are 47 of them.", reg) == []


# --- vocabulary ----------------------------------------------------------


def test_a_stated_constraint_is_recognised(reg):
    assert dims(parse_prose(DOC_EXTRACTION, reg))["data_residency"] == "cannot_leave"


def test_a_phrase_elsewhere_in_the_text_is_still_found(reg):
    assert dims(parse_prose(STUDIO, reg))["hosting"] == "air-gapped"


def test_the_absence_of_a_human_waiting_is_recognised(reg):
    """Whether someone is waiting decides how inference gets paid for."""
    assert dims(parse_prose(STUDIO, reg))["human_waiting"] == "no"


def test_interpretability_requirements_are_recognised(reg):
    assert dims(parse_prose(CHURN, reg))["interpretability_required"] is True


def test_nothing_is_extracted_from_text_that_says_nothing(reg):
    assert parse_prose("We would like to explore some options with AI.", reg) == []


def test_a_dimension_is_not_invented_from_a_near_miss(reg):
    """'cannot leave the meeting' is not a residency constraint."""
    assert "data_residency" not in dims(parse_prose("I cannot leave the meeting.", reg))


# --- provenance and traceability ----------------------------------------


def test_stated_facts_carry_artifact_provenance(reg):
    fact = next(f for f in parse_prose(DOC_EXTRACTION, reg) if f.dimension == "data_residency")
    assert fact.provenance is Provenance.ARTIFACT


def test_every_fact_points_back_at_the_words_that_produced_it(reg):
    """An FDE must be able to ask 'where did that come from' and get a sentence."""
    for fact in parse_prose(DOC_EXTRACTION, reg):
        assert fact.span
        excerpt = DOC_EXTRACTION[fact.span[0] : fact.span[1]]
        assert excerpt.strip()


def test_the_span_actually_contains_the_evidence(reg):
    fact = next(f for f in parse_prose(DOC_EXTRACTION, reg) if f.dimension == "corpus_size")
    assert "200,000" in DOC_EXTRACTION[fact.span[0] : fact.span[1]]


def test_the_source_is_named_so_two_documents_can_be_told_apart(reg):
    facts = parse_prose(DOC_EXTRACTION, reg, source="rfp.pdf")
    assert all(f.source == "rfp.pdf" for f in facts)


# --- playback ------------------------------------------------------------


def test_the_restatement_plays_back_what_was_understood(reg):
    """Said first, before any design. It is how an FDE finds out they misread."""
    said = restate(parse_prose(DOC_EXTRACTION, reg), reg)
    assert "200,000" in said or "200000" in said
    assert "cannot leave" in said.lower()


def test_the_restatement_says_so_when_nothing_was_understood(reg):
    assert "nothing" in restate([], reg).lower()


# --- across cases --------------------------------------------------------


def test_different_statements_yield_different_facts(reg):
    """If every brief parses to the same profile, the parser is not reading."""
    parsed = [
        frozenset(dims(parse_prose(text, reg)).items())
        for text in (DOC_EXTRACTION, STUDIO, ROUTE, CHURN)
    ]
    assert len(set(parsed)) == 4


def test_parsing_is_deterministic(reg):
    assert parse_prose(DOC_EXTRACTION, reg) == parse_prose(DOC_EXTRACTION, reg)


def test_parsing_needs_no_model(reg):
    """The air-gap requirement. There is nothing to call."""
    assert parse_prose(DOC_EXTRACTION, reg, model=None)
