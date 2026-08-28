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


# --- refusing to guess ---------------------------------------------------
#
# Silence is a safe failure: the interview picks the question up. A confident
# wrong answer is not, because it carries artifact provenance and will outrank
# the correction that arrives later. Everything below asserts silence.


def test_a_negated_phrase_is_not_read_as_the_phrase(reg):
    """'It is not the case that data cannot leave' is not a residency
    constraint. A matcher cannot tell which value the negation selects, so it
    must decline rather than pick one."""
    assert "data_residency" not in dims(
        parse_prose("It is not the case that data cannot leave.", reg)
    )


def test_a_plainly_stated_constraint_still_reads(reg):
    """The negation guard must not silence ordinary sentences."""
    assert dims(parse_prose("Data cannot leave the client environment.", reg))[
        "data_residency"
    ] == "cannot_leave"


def test_two_values_of_one_dimension_in_the_same_text_are_refused(reg):
    """'Cannot leave for EU, may leave for US' is a real requirement the
    framework cannot yet express. Picking whichever matched first would hide
    that behind a confident answer."""
    text = "Data cannot leave for EU clients, though data may leave for US ones."
    assert "data_residency" not in dims(parse_prose(text, reg))


def test_a_quantity_does_not_borrow_a_word_from_another_sentence(reg):
    """'We handle 200,000 cases. Separately, documents are archived.' -- the
    number and the word that would name it are about different things."""
    text = "We handle 200,000 cases. Separately, documents are archived."
    assert "corpus_size" not in dims(parse_prose(text, reg))


def test_a_quantity_and_its_unit_in_one_sentence_still_read(reg):
    assert dims(parse_prose("We hold 200,000 documents.", reg))["corpus_size"] == 200_000


def test_a_range_is_refused_rather_than_split_across_dimensions(reg):
    """'Between 8,000 and 12,000 documents are verified' is one quantity, and
    reading it as two different measurements is worse than reading neither."""
    text = "Between 8,000 and 12,000 documents are verified."
    got = dims(parse_prose(text, reg))
    assert "corpus_size" not in got
    assert "labelled_count" not in got


def test_scripts_the_parser_cannot_read_produce_silence_not_an_error(reg):
    """Non-Latin scripts are a known gap. Silence is the correct failure until
    it is closed -- it is recoverable, and the interview will ask."""
    assert parse_prose("डेटा क्लाइंट के वातावरण से बाहर नहीं जा सकता।", reg) == []


def test_a_more_specific_value_wins_over_the_one_it_refines(reg):
    """'Scanned supplier invoices' matches both scanned_documents and
    documents. That is not two answers competing, it is one answer stated
    precisely -- and refusing it would send the framework asking a question the
    brief already settled."""
    got = dims(parse_prose("We process scanned supplier invoices.", reg))
    assert got["input_format"] == "scanned_documents"


def test_two_values_neither_refining_the_other_are_still_refused(reg):
    """The refinement rule must not become a way of picking arbitrarily."""
    text = "Data cannot leave for EU clients, though data may leave for US ones."
    assert "data_residency" not in dims(parse_prose(text, reg))


# --- numbers people write as words -----------------------------------------


def test_word_numbers_count(reg):
    """'Two million records' is how a sponsor actually writes it. A scanner
    that only reads digits misses the corpus size in half of real briefs."""
    facts = dims(parse_prose("We hold two million records in total.", reg))
    assert facts.get("corpus_size") == 2_000_000


def test_small_word_counts_attach_to_their_noun(reg):
    facts = dims(parse_prose("Four external systems are involved.", reg))
    assert facts.get("external_systems") == 4


def test_one_is_deliberately_not_a_quantity(reg):
    """'one operation', 'one place', 'one answer' -- the word is everywhere
    in prose that is not counting anything. Excluded on purpose; a brief
    that means the number one writes 1."""
    facts = dims(parse_prose("Everything lands in one system of record.", reg))
    assert "external_systems" not in facts


# --- what the aegis battery caught: prose the framework read as silence -----


def test_from_last_year_is_not_a_range(reg):
    """'five thousand labelled from last year' held two quantities; the old
    range guard saw the word 'from' and threw the whole sentence away."""
    text = "Corpus is about 48000 reports, five thousand labelled from last year."
    facts = parse_prose(text, reg)
    values = {f.dimension: f.value for f in facts}
    assert values.get("corpus_size") == 48000
    assert values.get("labelled_count") == 5000


def test_a_numeric_range_is_still_declined(reg):
    facts = parse_prose("Volume is between 8,000 and 12,000 documents.", reg)
    assert not any(f.dimension == "corpus_size" for f in facts)


def test_a_duration_spoken_in_words(reg):
    facts = parse_prose("The budget is about two seconds per decision.", reg)
    assert any(f.dimension == "latency_budget_ms" and f.value == 2000 for f in facts)


def test_the_waiting_person_need_not_be_called_a_user(reg):
    facts = parse_prose("A safety officer is waiting on each triage decision.", reg)
    assert any(f.dimension == "human_waiting" and f.value == "yes" for f in facts)


def test_nobody_waiting_still_reads_as_no(reg):
    """The generic 'is waiting on' must not turn 'nobody is waiting on it'
    into an ambiguity refusal -- nobody is a negation, and the negation
    guard suppresses the yes-hit it sits in front of."""
    facts = parse_prose("Nobody is waiting on it, the job runs overnight.", reg)
    assert any(f.dimension == "human_waiting" and f.value == "no" for f in facts)


def test_the_customer_vpc_is_recognised_in_the_third_person(reg):
    """The value is named customer-vpc and 'runs in the customer VPC' read as
    nothing: every recogniser was first-person. An FDE's notes are written
    in the third."""
    facts = parse_prose("It runs in the customer VPC.", reg)
    assert any(f.dimension == "hosting" and f.value == "customer-vpc" for f in facts)


def test_the_operating_team_stated_in_the_third_person(reg):
    facts = parse_prose("The platform team operates it after handover.", reg)
    assert any(f.dimension == "operates_after_handover" and f.value == "platform_team"
               for f in facts)
