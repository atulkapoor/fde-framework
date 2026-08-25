"""Sample input/output pairs, the highest-value thing a client can hand over.

They do four jobs at once, which nothing else an FDE collects does: define the
output contract, seed the golden set, select the metric, and expose the hard
cases. A brief describes the problem; these describe the answer.
"""

import json

import pytest

from fde.intake.samples import (
    ContractConflict,
    assess,
    build_eval_set,
    infer_contract,
    infer_metrics,
    samples_to_facts,
    split_pairs,
)

PAIRS = [
    {"id": "a", "input": "Total due: $4,230.00\nVAT: $1,975.25",
     "output": {"total_due": 4230.0, "vat": 1975.25, "account": "****4471"},
     "verified": True, "layout": "boxed_form"},
    {"id": "b", "input": "Amount due ....... 1,100.00\nVAT ....... 500.00",
     "output": {"total_due": 1100.0, "vat": 500.0, "account": "****9931"},
     "verified": True, "layout": "dotted_leader"},
    {"id": "c", "input": "TOTAL 220.00 | VAT 80.00",
     "output": {"total_due": 220.0, "vat": 80.0, "account": "****2210",
                "withheld": 0.0},
     "verified": True, "layout": "pipe_table"},
    {"id": "d", "input": "unreadable scan",
     "output": {"total_due": 0.0, "vat": 0.0, "account": "****0001"},
     "verified": False, "layout": "boxed_form"},
]


# --- the contract falls out of the output side ---------------------------


def test_the_fields_come_from_what_was_produced_not_what_was_asked_for(reg=None):
    contract = infer_contract(PAIRS)
    assert {"total_due", "vat", "account"} <= set(contract.fields)


def test_a_field_absent_from_some_pairs_is_optional(reg=None):
    """Optional is decided by absence, not by a null. A field present and null
    is a different statement from a field nobody filled in."""
    contract = infer_contract(PAIRS)
    assert contract.fields["withheld"].required is False
    assert contract.fields["vat"].required is True


def test_types_are_read_from_the_values(reg=None):
    contract = infer_contract(PAIRS)
    assert contract.fields["total_due"].type == "number"
    assert contract.fields["account"].type == "string"


def test_an_identifier_is_classified_sensitive(reg=None):
    """This is what pins the field inside a boundary later. Getting it from the
    data rather than from a conversation is the point."""
    contract = infer_contract(PAIRS)
    assert contract.fields["account"].sensitivity == "identifier"
    assert contract.sensitive_fields == ["account"]


def test_two_pairs_with_the_same_input_and_different_outputs_are_refused(reg=None):
    """A spec bug in the client's own data. Averaging it away hides the one
    thing worth telling them."""
    contradictory = [
        {"id": "x", "input": "same", "output": {"total": 1}, "verified": True},
        {"id": "y", "input": "same", "output": {"total": 2}, "verified": True},
    ]
    with pytest.raises(ContractConflict) as exc:
        infer_contract(contradictory)
    assert "total" in str(exc.value)


# --- the metric follows the shape ----------------------------------------


def test_structured_output_is_scored_field_by_field(reg=None):
    assert infer_metrics(infer_contract(PAIRS)) == ["field_exact_match", "field_coverage"]


def test_freeform_output_has_to_be_judged(reg=None):
    prose = [{"id": "a", "input": "x", "output": "a paragraph of prose", "verified": True}]
    assert "judged" in infer_metrics(infer_contract(prose))


# --- splitting -----------------------------------------------------------


def test_the_split_is_deterministic(reg=None):
    assert split_pairs(PAIRS, seed=0).golden_ids == split_pairs(PAIRS, seed=0).golden_ids


def test_nothing_appears_in_both_halves(reg=None):
    split = split_pairs(PAIRS, seed=0)
    assert not (set(split.golden_ids) & set(split.holdout_ids))


def test_unverified_pairs_go_to_neither(reg=None):
    """They cannot be ground truth. They are mined instead."""
    split = split_pairs(PAIRS, seed=0)
    assert "d" not in split.golden_ids and "d" not in split.holdout_ids
    assert "d" in split.mine_ids


# --- three layers, not one -----------------------------------------------


def test_the_eval_set_has_three_layers(reg=None):
    """Golden alone measures the happy path. Edge and adversarial are where
    production failures live."""
    suite = build_eval_set(PAIRS)
    assert suite.golden and suite.edge_case and suite.adversarial


def test_edge_cases_come_from_the_layouts_that_differ_most(reg=None):
    suite = build_eval_set(PAIRS)
    assert {c["layout"] for c in suite.edge_case} - {"boxed_form"}


def test_the_adversarial_layer_is_built_from_the_contract(reg=None):
    """Not from the pairs. Everything the contract forbids is a test nobody
    supplied, and those are the ones a client never thinks of."""
    suite = build_eval_set(PAIRS)
    kinds = {c["kind"] for c in suite.adversarial}
    assert {"missing_required", "type_violation", "prompt_injection"} <= kinds


def test_the_injection_case_targets_the_input_not_the_schema(reg=None):
    suite = build_eval_set(PAIRS)
    injection = next(c for c in suite.adversarial if c["kind"] == "prompt_injection")
    assert "ignore" in injection["input"].lower()


# --- facts ---------------------------------------------------------------


def test_pairs_settle_dimensions_nobody_had_to_be_asked(reg=None):
    facts = {f.dimension: f.value for f in samples_to_facts(PAIRS)}
    assert facts["output_shape"] == "structured"
    assert facts["labelled_count"] == 3
    assert facts["corpus_size"] == 4


def test_a_sensitive_field_settles_residency_as_a_question_worth_asking(reg=None):
    facts = {f.dimension: f.value for f in samples_to_facts(PAIRS)}
    assert facts.get("sensitivity_present") is True


# --- honesty about how many ----------------------------------------------


def test_too_few_pairs_is_reported_with_the_number(reg=None):
    """'Not many' is not actionable. 'Three, and you want fifty' is."""
    warnings = assess(PAIRS[:2])
    assert warnings and "2" in warnings[0]


def test_enough_pairs_produces_no_warning(reg=None):
    assert assess([{**PAIRS[0], "id": str(n)} for n in range(80)]) == []


def test_pairs_load_from_a_jsonl_file(tmp_path):
    from fde.intake.samples import load_pairs

    path = tmp_path / "pairs.jsonl"
    path.write_text("\n".join(json.dumps(p) for p in PAIRS))
    assert len(load_pairs(path)) == len(PAIRS)


def test_a_field_naming_mismatch_between_pairs_is_reported(tmp_path):
    from fde.intake.samples import load_pairs

    path = tmp_path / "pairs.jsonl"
    path.write_text('{"id": "a"}\n')
    with pytest.raises(ValueError, match="output"):
        load_pairs(path)
