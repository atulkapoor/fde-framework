"""Turning what someone said into a fact, or refusing to.

Every branch here is a thing an FDE actually types. An unusable answer
stored anyway becomes a wrong fact at artifact strength, so refusal --
the sharpening probe -- matters more than acceptance, and every refusal
path deserves the same coverage as the happy one.
"""

from pathlib import Path

from fde.intake.answers import parse_answer
from fde.models.schema import Dimension, ValueType
from fde.registry import load_registry

REGISTRY = load_registry(Path(__file__).resolve().parents[1] / "framework")


def dim(kind, **extra):
    return Dimension(id="d", type=kind, **extra)


# --- skipping is legal -----------------------------------------------------


def test_the_ways_people_say_they_do_not_know_all_skip():
    for reply in ("", "?", "idk", "don't know", "skip", "  pass  "):
        answer = parse_answer(dim(ValueType.COUNT), reply)
        assert answer.skipped and not answer.usable, reply


# --- enums accept the way people talk --------------------------------------


def test_an_enum_accepts_a_recognised_phrase_not_only_the_value():
    """The same vocabulary the prose parser uses; two ways of recognising
    the same thing would drift apart."""
    hosting = dim(ValueType.ENUM, values=["air-gapped", "on-prem"],
                  recognises={"air-gapped": ["no network egress"]})
    assert parse_answer(hosting, "we have no network egress at all").value == "air-gapped"


def test_an_enum_probe_names_the_legal_values():
    hosting = dim(ValueType.ENUM, values=["air-gapped", "on-prem"])
    answer = parse_answer(hosting, "the cloud, mostly")
    assert not answer.usable
    assert "air-gapped" in answer.probe


# --- durations -------------------------------------------------------------


def test_durations_normalise_to_milliseconds():
    assert parse_answer(dim(ValueType.DURATION_MS), "800ms").value == 800
    assert parse_answer(dim(ValueType.DURATION_MS), "2s").value == 2000
    assert parse_answer(dim(ValueType.DURATION_MS), "1.5 seconds").value == 1500
    assert parse_answer(dim(ValueType.DURATION_MS), "3 min").value == 180_000


def test_fast_is_not_a_duration():
    """The module's founding example: 'fast' does not parse, and nothing
    needs to reason about that."""
    answer = parse_answer(dim(ValueType.DURATION_MS), "fast")
    assert not answer.usable
    assert "p95" in answer.probe


# --- counts and money ------------------------------------------------------


def test_counts_accept_commas_and_scale_suffixes():
    assert parse_answer(dim(ValueType.COUNT), "200,000").value == 200_000
    assert parse_answer(dim(ValueType.COUNT), "200k").value == 200_000
    assert parse_answer(dim(ValueType.COUNT), "1.5m").value == 1_500_000
    assert parse_answer(dim(ValueType.COUNT), "2bn").value == 2_000_000_000


def test_money_parses_like_a_count():
    assert parse_answer(dim(ValueType.MONEY), "50k").value == 50_000


def test_a_lot_is_not_a_count():
    answer = parse_answer(dim(ValueType.COUNT), "a lot")
    assert not answer.usable
    assert "200k" in answer.probe


# --- booleans --------------------------------------------------------------


def test_booleans_accept_the_words_people_use():
    for reply, expected in (("yes", True), ("required", True), ("must", True),
                            ("no", False), ("optional", False),
                            ("not required", False)):
        assert parse_answer(dim(ValueType.BOOLEAN), reply).value is expected, reply


def test_maybe_is_not_a_boolean():
    answer = parse_answer(dim(ValueType.BOOLEAN), "maybe")
    assert not answer.usable


# --- ratios ----------------------------------------------------------------


def test_ratios_accept_percent_and_fraction_forms():
    assert parse_answer(dim(ValueType.RATIO), "90%").value == 0.9
    assert parse_answer(dim(ValueType.RATIO), "0.9").value == 0.9


def test_most_of_them_is_not_a_ratio():
    answer = parse_answer(dim(ValueType.RATIO), "most of them")
    assert not answer.usable
    assert "90%" in answer.probe


# --- free text -------------------------------------------------------------


def test_text_dimensions_take_the_reply_as_given():
    assert parse_answer(dim(ValueType.TEXT), "days to close the quarter").value == \
        "days to close the quarter"


# --- the interview and the prose parser must read the same words alike ------


def test_hybrid_phrases_do_not_record_as_on_prem():
    """"on-prem with cloud burst" typed at the interview prompt once recorded
    on-prem -- the substring won by declaration order -- while fde frame read
    the identical words as hybrid. One vocabulary, one resolution."""
    hosting = REGISTRY.dimensions["hosting"]
    for phrase in ("sensitive stays on-prem", "on-prem with cloud burst",
                   "split between on-prem and cloud"):
        answer = parse_answer(hosting, phrase)
        assert answer.value == "hybrid", phrase


def test_a_negated_phrase_is_not_an_answer():
    hosting = REGISTRY.dimensions["hosting"]
    answer = parse_answer(hosting, "definitely not on-prem")
    assert answer.value is None


def test_two_values_that_do_not_refine_each_other_get_a_probe():
    hosting = REGISTRY.dimensions["hosting"]
    answer = parse_answer(hosting, "managed api for some, air-gapped for the rest")
    assert answer.value is None
    assert answer.probe and "which one" in answer.probe
