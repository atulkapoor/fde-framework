"""Sample input/output pairs, the highest-value thing a client can hand over.

They do four jobs at once, which nothing else an FDE collects does: define the
output contract, seed the golden set, select the metric, and expose the hard
cases. A brief describes the problem; these describe the answer.
"""

import json
from collections import Counter

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
     "output": {"total_due": 4230.0, "vat": 1975.25, "invoice_no": "INV-4471"},
     "verified": True, "layout": "boxed_form"},
    {"id": "b", "input": "Amount due ....... 1,100.00\nVAT ....... 500.00",
     "output": {"total_due": 1100.0, "vat": 500.0, "invoice_no": "INV-9931"},
     "verified": True, "layout": "dotted_leader"},
    {"id": "c", "input": "TOTAL 220.00 | VAT 80.00",
     "output": {"total_due": 220.0, "vat": 80.0, "invoice_no": "INV-2210",
                "discount": 0.0},
     "verified": True, "layout": "pipe_table"},
    {"id": "d", "input": "unreadable scan",
     "output": {"total_due": 0.0, "vat": 0.0, "invoice_no": "INV-0001"},
     "verified": False, "layout": "boxed_form"},
]


# --- the contract falls out of the output side ---------------------------


def test_the_fields_come_from_what_was_produced_not_what_was_asked_for(reg=None):
    contract = infer_contract(PAIRS)
    assert {"total_due", "vat", "invoice_no"} <= set(contract.fields)


def test_a_field_absent_from_some_pairs_is_optional(reg=None):
    """Optional is decided by absence, not by a null. A field present and null
    is a different statement from a field nobody filled in."""
    contract = infer_contract(PAIRS)
    assert contract.fields["discount"].required is False
    assert contract.fields["vat"].required is True


def test_types_are_read_from_the_values(reg=None):
    contract = infer_contract(PAIRS)
    assert contract.fields["total_due"].type == "number"
    assert contract.fields["invoice_no"].type == "string"


def test_an_identifier_is_classified_sensitive(reg=None):
    """This is what pins the field inside a boundary later. Getting it from the
    data rather than from a conversation is the point."""
    contract = infer_contract(PAIRS)
    assert contract.fields["invoice_no"].sensitivity == "identifier"
    assert contract.sensitive_fields == ["invoice_no"]


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


def test_the_adversarial_layer_is_executable(reg=None):
    """The earlier layer emitted prose probes compared against prose
    expectations -- unpassable by construction, 0% forever. A probe is only
    a probe if the pipeline can be run on it: a mutated real input, expecting
    the same correct answer or a refusal."""
    suite = build_eval_set(PAIRS)
    kinds = {c["kind"] for c in suite.adversarial}
    assert {"prompt_injection", "empty_input"} <= kinds
    for case in suite.adversarial:
        assert "output" in case or case.get("expect_refusal"), case["kind"]


def test_injection_must_not_change_the_answer(reg=None):
    """The injected case expects the ORIGINAL pair's output: a system that
    follows text inside the document fails by disagreeing with itself."""
    suite = build_eval_set(PAIRS)
    injection = next(c for c in suite.adversarial if c["kind"] == "prompt_injection")
    assert "ignore" in injection["input"].lower()
    assert injection["output"] in [p["output"] for p in PAIRS]


def test_dict_inputs_get_field_level_probes(reg=None):
    pairs = [{"id": str(i), "verified": True,
              "input": {"note": f"unit {i}", "sensor": {"vibration": 3.0 + i}},
              "output": {"disposition": "pass"}} for i in range(6)]
    suite = build_eval_set(pairs)
    kinds = {c["kind"] for c in suite.adversarial}
    assert {"prompt_injection", "type_violation", "missing_field"} <= kinds
    violation = next(c for c in suite.adversarial if c["kind"] == "type_violation")
    assert violation["input"]["sensor"]["vibration"] == "four thousand"
    assert violation.get("expect_refusal")


# --- facts ---------------------------------------------------------------


def test_pairs_settle_only_what_they_actually_settle(reg=None):
    """The shape, yes -- examples of the output decide it. The counts, no: a
    sample file cannot say whether it is the whole labelled set or a
    three-line excerpt, and emitting len(pairs) as corpus_size once let an
    attachment's line count silently outvote a client's stated two hundred
    thousand."""
    facts = {f.dimension: f.value for f in samples_to_facts(PAIRS)}
    assert facts["output_shape"] == "structured"
    assert "labelled_count" not in facts
    assert "corpus_size" not in facts


def test_a_sensitive_field_settles_residency_as_a_question_worth_asking(reg=None):
    facts = {f.dimension: f.value for f in samples_to_facts(PAIRS)}
    assert facts.get("sensitivity_present") is True


# --- honesty about how many ----------------------------------------------


def test_too_few_pairs_is_reported_with_the_number(reg=None):
    """'Not many' is not actionable. 'Three, and you want fifty' is."""
    warnings = assess(PAIRS[:2])
    assert warnings and "2" in warnings[0]


def test_enough_pairs_produces_no_warning(reg=None):
    # Distinct inputs of distinct lengths: the same line eighty times is a
    # duplicate cluster, and eighty lines of one length is a truncation.
    distinct = [{**PAIRS[0], "id": str(n), "input": PAIRS[0]["input"] + "\nRef: " + "x" * n}
                for n in range(80)]
    assert assess(distinct) == []


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


def test_a_single_label_field_is_a_decision_not_a_structured_record():
    """{"disposition": "pass"} is a verdict. Calling it structured once
    silently corrected a client's stated decision with the contract's own
    misreading -- both spoke at artifact strength, and the later won."""
    pairs = [{"id": str(i), "input": {"u": i},
              "output": {"disposition": "pass" if i % 3 else "repair"}}
             for i in range(9)]
    assert infer_contract(pairs).shape == "decision"


def test_many_fields_stay_structured():
    pairs = [{"id": str(i), "input": {"u": i},
              "output": {"vendor": f"v{i}", "total": i}} for i in range(4)]
    assert infer_contract(pairs).shape == "structured"


def test_rarity_is_relative_to_the_corpus_balance(reg=None):
    """Two polymer units among forty machined are the shape the system
    fails on first; the old absolute rule (n <= 1) called them common."""
    pairs = [{"id": str(i), "verified": True, "layout": "machined",
              "input": f"doc {i}", "output": {"total": float(i)}}
             for i in range(40)]
    pairs += [{"id": f"p{i}", "verified": True, "layout": "polymer",
               "input": f"poly {i}", "output": {"total": 1.0}} for i in range(2)]
    suite = build_eval_set(pairs)
    assert any(c["layout"] == "polymer" for c in suite.edge_case)


def test_one_layout_means_nothing_is_rare(reg=None):
    pairs = [{"id": str(i), "verified": True, "layout": "same",
              "input": f"doc {i}", "output": {"total": float(i)}}
             for i in range(10)]
    edges = build_eval_set(pairs).edge_case
    # Nothing is rare; the only edge-layer entries are the probes' bases,
    # which ship there so the harness can score each base un-steered.
    assert all(e.get("edge", "").startswith("probe base") for e in edges), edges


def test_probe_bases_are_typical_cases_that_leave_golden(reg=None):
    """Built on the two shortest inputs, every probe once sat on a case the
    baseline misreads. Bases are one typical-length case per label; they
    ship in the edge layer, leave golden, and every probe names its base."""
    suite = build_eval_set(labelled_pairs(48))
    bases = [e for e in suite.edge_case if e.get("edge", "").startswith("probe base")]
    assert len(bases) == 3 and len({b["output"]["decision"] for b in bases}) == 3
    golden_ids = {g["id"] for g in suite.golden}
    assert not {b["id"] for b in bases} & golden_ids
    base_ids = {b["id"] for b in bases}
    for probe in suite.adversarial:
        if probe.get("base_id"):
            assert probe["base_id"] in base_ids, probe["id"]
    lengths = sorted(len(g["input"]) for g in labelled_pairs(48))
    median = lengths[len(lengths) // 2]
    assert all(abs(len(b["input"]) - median) <= 3 for b in bases)


# --- the split: one case once, every label on both sides ------------------


def labelled_pairs(n: int = 30, labels=("a", "b", "c")) -> list[dict]:
    return [{"id": f"p{i}", "input": f"text number {i} about {labels[i % 3]}",
             "output": {"decision": labels[i % 3]}, "verified": True}
            for i in range(n)]


def test_a_repeated_input_is_counted_once(reg=None):
    pairs = labelled_pairs() + [{"id": "again", "input": "text number 1 about b",
                                 "output": {"decision": "b"}, "verified": True}]
    split = split_pairs(pairs)
    assert split.duplicate_ids == ["again"]
    assert "again" not in split.golden_ids and "again" not in split.holdout_ids


def test_the_holdout_is_stratified_by_label(reg=None):
    """Drawn by hash alone, a holdout once held 16/15/14 of three labels
    against a golden set of 46/36/23: every per-class number compared two
    mixes. Each label is held out in the same share."""
    split = split_pairs(labelled_pairs(60))
    by_id = {p["id"]: p for p in labelled_pairs(60)}
    held = Counter(by_id[i]["output"]["decision"] for i in split.holdout_ids)
    assert set(held) == {"a", "b", "c"} and max(held.values()) - min(held.values()) <= 1


def test_freeform_answers_are_not_labels(reg=None):
    """Five answers for five pairs are answers: stratifying by them once
    held every pair out and shipped an empty golden set."""
    pairs = [{"id": f"q{i}", "input": f"Question {i}?", "output": f"Answer {i}.",
              "verified": True} for i in range(10)]
    split = split_pairs(pairs)
    assert len(split.golden_ids) == 7 and len(split.holdout_ids) == 3


def test_edges_move_out_of_golden_when_golden_keeps_a_floor(reg=None):
    """A baseline fitted on the golden file would score copied edges
    in-sample and count them twice; the probes build on the edges."""
    suite = build_eval_set(labelled_pairs(48))
    golden_ids = {c["id"] for c in suite.golden}
    assert suite.edge_case and not {e["id"] for e in suite.edge_case} & golden_ids
    assert all(not e.get("in_sample") for e in suite.edge_case)
    assert all(not p.get("in_sample") for p in suite.adversarial)
    steered = [p for p in suite.adversarial if "steered_toward" in p]
    assert len(steered) == 2 and all(p["steered_toward"] != p["output"] for p in steered)


def test_a_tiny_corpus_keeps_its_edges_in_golden_and_says_so(reg=None):
    suite = build_eval_set(PAIRS)
    assert suite.golden, "four pairs are four cases, not an exam with two layers"
    assert all(e.get("in_sample") for e in suite.edge_case)


def test_an_intent_catalogue_is_a_decision_however_many_intents(reg=None):
    """Seventy-seven support-queue intents over thousands of messages are
    labels: every value repeats and there are far fewer values than pairs.
    A cap of five once read them as structured records."""
    intents = [f"intent_{n}" for n in range(77)]
    pairs = [{"id": f"m{i}", "input": f"message {i}", "verified": True,
              "output": {"intent": intents[i % 77]}} for i in range(770)]
    assert infer_contract(pairs).shape == "decision"


def test_one_field_of_unique_values_is_still_a_record(reg=None):
    pairs = [{"id": f"r{i}", "input": f"doc {i}", "verified": True,
              "output": {"reference": f"INV-{i:04d}"}} for i in range(40)]
    assert infer_contract(pairs).shape == "structured"



def test_one_rare_label_does_not_turn_a_catalogue_into_records(reg=None):
    """Seventy-seven repeating intents plus one seen once are still a label
    set; requiring every value to repeat once flipped the shape and built
    with no reasoning component."""
    intents = [f"intent_{n}" for n in range(77)]
    pairs = [{"id": f"m{i}", "input": f"message {i}", "verified": True,
              "output": {"intent": intents[i % 77]}} for i in range(770)]
    pairs.append({"id": "rare", "input": "a message like no other", "verified": True,
                  "output": {"intent": "intent_rare"}})
    assert infer_contract(pairs).shape == "decision"
    split = split_pairs(pairs)
    assert "rare" in split.golden_ids  # a singleton is learned from, never held out
