"""What to build for each component, and why.

Three properties matter more than the selection itself.

**The simplest thing that applies wins.** Not the most capable. A framework that
reaches for the most sophisticated option available is the failure this exists
to prevent.

**Every decision names what it rejected, and why.** A recommendation with no
rejected alternatives has not been made; it has been assumed.

**Confidence must clear the cost of being wrong.** A choice that takes an
afternoon to undo can be made on a hunch. One that cannot be undone cannot.
"""

from pathlib import Path

import pytest

from fde.decide import decide_all, decide_component
from fde.decompose import decompose
from fde.models.base import Confidence, Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.models.schema import Reversibility
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def values(**kw):
    return kw


DOC_EXTRACTION = values(
    output_shape="structured", corpus_size=200_000, labelled_count=8_000,
    data_residency="cannot_leave", hosting="air-gapped",
)
CHURN = values(output_shape="classification", corpus_size=2_000_000,
               interpretability_required=True, latency_budget_ms=10)
STUDIO = values(output_shape="freeform", hosting="air-gapped", human_waiting="no")
ROUTE = values(output_shape="decision", latency_budget_ms=200)


# --- the right answer, not the fashionable one ---------------------------


def test_structured_extraction_is_deterministic_not_generative(reg):
    """Correctness is non-negotiable when mapping a field. 'The model will
    handle it' is the wrong answer here."""
    decision = decide_component("representation", DOC_EXTRACTION, reg)
    assert decision.approach == "deterministic"


def test_a_tabular_prediction_that_must_be_explained_is_not_a_language_model(reg):
    decision = decide_component("representation", CHURN, reg)
    assert decision.approach == "classical-ml"


def test_a_constraint_bearing_problem_goes_to_a_solver(reg):
    """Optimisation makes decisions; machine learning makes predictions."""
    assert decide_component("planning", ROUTE, reg).approach == "optimisation"


def test_a_generative_task_does_reach_for_a_model(reg):
    """The restraint rule must not become a refusal to ever use one."""
    assert decide_component("reasoning", STUDIO, reg).approach in {"finetune", "llm"}


def test_the_simplest_applicable_approach_wins(reg):
    """Not the most capable. Reaching for the fanciest option that fits is the
    failure this whole thing exists to prevent."""
    decision = decide_component("representation", DOC_EXTRACTION, reg)
    rejected = {r.id for r in decision.rejected}
    assert "llm" in rejected or "llm" not in {decision.approach}


# --- rejected alternatives -----------------------------------------------


def test_every_decision_names_what_it_rejected(reg):
    """A recommendation with no rejected alternatives has been assumed, not made
    -- unless the registry genuinely offers none, which is said out loud rather
    than left as silence a client would read as 'considered and dismissed'."""
    for decision in decide_all(DOC_EXTRACTION, reg).decided().values():
        assert decision.rejected or decision.uncontested


def test_an_uncontested_decision_says_it_was_uncontested(lone_approach):
    """One candidate is not the same as one winner. Tested against a registry
    built to be thin, since the shipped one no longer is."""
    decision = decide_component("widget", {"output_shape": "structured"}, lone_approach)
    assert decision.uncontested
    assert "only approach registered" in decision.rationale


def test_a_component_with_only_one_candidate_approach_is_a_registry_gap(lone_approach):
    """Nothing to weigh means the corpus is thin there, and gaps should say so."""
    from fde.graph import find_gaps

    assert any(g.kind == "component_without_alternatives" for g in find_gaps(lone_approach))


@pytest.fixture
def lone_approach(tmp_path):
    """A component served by exactly one approach."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "widget.md").write_text(
        "---\nid: widget\nname: Widget\nrequired_when: [always]\n---\n"
    )
    (tmp_path / "dimensions").mkdir()
    (tmp_path / "dimensions" / "output_shape.md").write_text(
        "---\nid: output_shape\ntype: enum\nvalues: [structured, freeform]\n---\n"
    )
    (tmp_path / "approaches").mkdir()
    (tmp_path / "approaches" / "only-one.md").write_text(
        "---\nid: only-one\nname: Only one\ncomponents: [widget]\n"
        "applies_when: [output_shape == structured]\n"
        "avoid_when: [output_shape == freeform]\n---\n"
    )
    return load_registry(tmp_path)


def test_every_rejection_states_a_reason(reg):
    for decision in decide_all(DOC_EXTRACTION, reg).decided().values():
        for rejection in decision.rejected:
            assert rejection.reason


def test_a_rejection_names_the_condition_that_ruled_it_out(reg):
    decision = decide_component("representation", CHURN, reg)
    reasons = " ".join(r.reason for r in decision.rejected)
    assert "output_shape" in reasons or "interpretability" in reasons


# --- evidence and confidence ---------------------------------------------


def test_every_decision_carries_evidence(reg):
    for decision in decide_all(DOC_EXTRACTION, reg).decided().values():
        assert decision.evidence is not None


def test_confidence_must_clear_the_cost_of_being_wrong(reg):
    """A one-way choice on a hunch is the expensive mistake."""
    for decision in decide_all(DOC_EXTRACTION, reg).decided().values():
        if decision.reversibility is Reversibility.ONE_WAY:
            assert decision.confidence is Confidence.HIGH


def test_an_undecidable_component_says_so_rather_than_picking_something(reg):
    """Nothing known, nothing decided. Silence beats a default."""
    decision = decide_component("representation", {}, reg)
    assert decision is None or decision.approach is None


# --- the outcome ---------------------------------------------------------


def test_four_problems_produce_four_different_architectures(reg):
    """The decisive test. If these collapse, the engine is defaulting."""
    shapes = {
        decide_all(case, reg).fingerprint()
        for case in (DOC_EXTRACTION, CHURN, STUDIO, ROUTE)
    }
    assert len(shapes) == 4


def test_the_fingerprint_is_stable_for_the_same_inputs(reg):
    once = decide_all(DOC_EXTRACTION, reg).fingerprint()
    assert once == decide_all(DOC_EXTRACTION, reg).fingerprint()


def test_the_fingerprint_changes_when_a_decision_changes(reg):
    a = decide_all(DOC_EXTRACTION, reg).fingerprint()
    b = decide_all({**DOC_EXTRACTION, "output_shape": "freeform"}, reg).fingerprint()
    assert a != b


def test_a_component_in_scope_that_cannot_be_filled_is_reported_not_dropped(reg):
    """The hole has to be visible. A component that disappears between
    "you need this" and "here is the design" is found at build time."""
    decisions = decide_all(DOC_EXTRACTION, reg)
    assert set(decisions) > set(decisions.decided())
    assert decisions.undecided()


def test_an_unfillable_component_does_not_change_the_fingerprint(reg):
    """What cannot be built is not part of what gets built."""
    once = decide_all(DOC_EXTRACTION, reg).fingerprint()
    assert once == decide_all(DOC_EXTRACTION, reg).decided_fingerprint()


def test_decisions_cover_the_components_that_were_decomposed(reg):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in DOC_EXTRACTION.items()])
    graph = decompose(p, reg)
    decisions = decide_all(DOC_EXTRACTION, reg, components=list(graph.components))
    assert set(decisions) <= set(graph.components)


# --- divergence, with a real outcome -------------------------------------


def test_divergence_now_measures_the_architecture(reg):
    """The placeholder outcome measured what got settled. This measures what
    gets built, which is the question actually worth asking."""
    from fde.decide import architecture_outcome
    from fde.intake.interview import divergence
    from fde.space import Space

    space = Space.from_registry(reg)
    result = divergence("data_residency", space, outcome=architecture_outcome(reg))
    assert result.considered >= 2


def test_a_dimension_that_does_not_move_the_architecture_scores_zero(reg):
    from fde.decide import architecture_outcome
    from fde.intake.interview import divergence
    from fde.space import Space

    space = Space.from_registry(reg).answer("output_shape", "classification")
    scored = divergence("embeddings", space, outcome=architecture_outcome(reg))
    assert scored.score == 0.0
