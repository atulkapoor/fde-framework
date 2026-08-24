"""Every component in scope can actually be filled.

A component with no approach cannot be emitted, so the graph carries a hole
through to build time. These tests close that, and pin the discriminations that
matter most in each.
"""

from pathlib import Path

import pytest

from fde.decide import decide_all, decide_component
from fde.decompose import decompose
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def profile(**values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    return p


# --- retrieval: the graph question ---------------------------------------


def test_a_single_fact_lookup_does_not_get_a_knowledge_graph(reg):
    """Graph retrieval measurably loses to plain chunks on lookup, and costs
    2-3x the latency to lose by. Reaching for it here is the expensive habit."""
    decision = decide_component(
        "retrieval", dict(output_shape="freeform", query_pattern="lookup"), reg
    )
    assert decision.approach != "graph-retrieval"


def test_multi_hop_questions_earn_the_graph(reg):
    """Where similarity search structurally cannot answer -- how these two
    things connect -- the graph is worth its construction cost."""
    decision = decide_component(
        "retrieval", dict(output_shape="freeform", query_pattern="multi_hop"), reg
    )
    assert decision.approach == "graph-retrieval"


def test_the_cheapest_retrieval_that_answers_the_question_wins(reg):
    decision = decide_component(
        "retrieval", dict(output_shape="freeform", query_pattern="lookup"), reg
    )
    assert decision.approach == "keyword-search"


def test_rejecting_the_graph_says_why(reg):
    decision = decide_component(
        "retrieval", dict(output_shape="freeform", query_pattern="lookup"), reg
    )
    reasons = " ".join(r.reason for r in decision.rejected)
    assert "query_pattern" in reasons


# --- evaluation follows what comes out -----------------------------------


def test_structured_output_is_scored_field_by_field(reg):
    assert decide_component("evaluation", dict(output_shape="structured"), reg).approach == (
        "field-match"
    )


def test_a_prediction_is_scored_against_labels(reg):
    assert decide_component("evaluation", dict(output_shape="classification"), reg).approach == (
        "labelled-metrics"
    )


def test_freeform_output_has_to_be_judged(reg):
    assert decide_component("evaluation", dict(output_shape="freeform"), reg).approach == "judged"


def test_an_air_gap_cannot_use_a_judge_that_calls_out(reg):
    """Offline evaluability. A metric that needs a hosted model is not a metric
    you have, and discovering that at deployment is too late."""
    decision = decide_component(
        "evaluation", dict(output_shape="freeform", hosting="air-gapped"), reg
    )
    assert decision.approach != "judged-hosted"


# --- perception follows what goes in -------------------------------------


def test_scanned_documents_need_more_than_a_text_read(reg):
    assert decide_component("perception", dict(input_format="scanned_documents"), reg).approach == (
        "ocr-pipeline"
    )


def test_data_that_arrives_structured_is_not_re_parsed(reg):
    """The cheapest perception is none."""
    assert decide_component("perception", dict(input_format="structured_data"), reg).approach == (
        "passthrough"
    )


# --- integration ---------------------------------------------------------


def test_touching_more_than_one_system_goes_through_a_governed_boundary(reg):
    """One entry point for auth, authorisation and audit, rather than each
    component calling out on its own account."""
    decision = decide_component(
        "integration", dict(output_shape="decision", external_systems=4), reg
    )
    assert decision.approach == "governed-tools"


def test_a_single_call_does_not_need_a_tool_registry(reg):
    decision = decide_component(
        "integration", dict(output_shape="decision", external_systems=1), reg
    )
    assert decision.approach == "direct-call"


# --- nothing is left unfilled --------------------------------------------


def test_the_worked_case_leaves_no_component_unfilled(reg):
    """A component in scope with no approach is a hole carried to build time."""
    values = dict(
        output_shape="structured", input_format="documents", query_pattern="lookup",
        corpus_size=200_000, labelled_count=8_000, data_residency="cannot_leave",
        hosting="air-gapped", latency_budget_ms=800, external_systems=2,
        operates_after_handover="platform_team",
    )
    graph = decompose(profile(**values), reg)
    decisions = decide_all(values, reg, components=list(graph.components))
    assert decisions.undecided() == []


def test_every_component_has_at_least_one_approach_serving_it(reg):
    serving = {c for a in reg.approaches.values() for c in a.components}
    assert set(reg.components) <= serving


def test_no_component_is_left_without_an_alternative(reg):
    """Nothing to weigh means the corpus is thin there, and a decision with a
    single candidate is uncontested rather than reasoned."""
    from fde.graph import find_gaps

    thin = [g.detail for g in find_gaps(reg) if g.kind == "component_without_alternatives"]
    assert not thin, f"only one approach serves: {thin}"
