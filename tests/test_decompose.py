"""Profile into a component graph.

A component is included only when something requires it, and it records what.
Spurious components are how a scope doubles between the workshop and the
statement of work, so "we might need retrieval" is not a reason to include
retrieval.
"""

from pathlib import Path

import pytest

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


# --- inclusion -----------------------------------------------------------


def test_always_required_components_are_always_present(reg):
    graph = decompose(Profile(), reg)
    assert {"perception", "evaluation", "observability"} <= set(graph.components)


def test_a_component_nothing_requires_is_excluded(reg):
    """The scope-doubling failure, guarded."""
    assert "memory" not in decompose(Profile(), reg).components


def test_labelled_data_brings_in_what_it_implies(reg):
    graph = decompose(profile(labelled_count=8000, corpus_size=200000), reg)
    assert "representation" in graph.components


def test_a_residency_constraint_requires_governance(reg):
    assert "governance" in decompose(profile(data_residency="cannot_leave"), reg).components


def test_governance_is_needed_either_way_and_differs_in_kind(reg):
    """An audit trail is needed whenever actions are taken on someone's behalf.
    Residency decides whether a boundary is enforced around them, not whether
    anything is recorded at all."""
    for residency in ("cannot_leave", "may_leave"):
        assert "governance" in decompose(profile(data_residency=residency), reg).components


def test_explaining_a_decision_is_a_separate_component(reg):
    """A boundary answers where data may go; accountability answers why this
    outcome. A system can need both, and folding them together means whichever
    fires first hides the other."""
    graph = decompose(profile(interpretability_required=True), reg)
    assert "accountability" in graph.components


def test_a_residency_constraint_alone_does_not_require_explanations(reg):
    graph = decompose(profile(data_residency="cannot_leave"), reg)
    assert "governance" in graph.components
    assert "accountability" not in graph.components


def test_an_unresolved_dimension_requires_nothing(reg):
    """Not knowing is not a reason to include something. The gate will say so."""
    assert "governance" not in decompose(Profile(), reg).components


# --- tracing -------------------------------------------------------------


def test_every_component_records_why_it_is_there(reg):
    graph = decompose(profile(data_residency="cannot_leave"), reg)
    for component in graph.components.values():
        assert component.because


def test_the_reason_names_the_condition_that_fired(reg):
    graph = decompose(profile(data_residency="cannot_leave"), reg)
    assert any("data_residency" in reason for reason in graph.components["governance"].because)


def test_a_component_required_twice_records_both_reasons(reg):
    graph = decompose(profile(data_residency="cannot_leave", hosting="air-gapped"), reg)
    assert len(graph.components["governance"].because) >= 2


# --- shape ---------------------------------------------------------------


def test_the_graph_carries_the_quality_ceiling_ordering(reg):
    """Perception caps what follows it, and the graph has to know that or
    'where do I look first' has no answer."""
    graph = decompose(profile(corpus_size=200000, labelled_count=8000), reg)
    assert graph.earliest_cap("reasoning") == "perception"


def test_different_problems_decompose_differently(reg):
    """If every profile yields the same graph, this is not deciding anything."""
    shapes = {
        frozenset(decompose(p, reg).components)
        for p in (
            profile(output_shape="structured", corpus_size=200000, labelled_count=8000),
            profile(output_shape="freeform", corpus_size=2000000),
            profile(output_shape="decision", latency_budget_ms=200),
        )
    }
    assert len(shapes) == 3


def test_a_classifier_does_not_get_a_reasoning_loop(reg):
    """Having a corpus is not a reason to put an LLM in front of it."""
    graph = decompose(profile(output_shape="classification", corpus_size=2000000), reg)
    assert "representation" in graph.components
    assert "reasoning" not in graph.components


def test_a_generative_task_does(reg):
    assert "reasoning" in decompose(profile(output_shape="freeform"), reg).components


def test_the_same_components_for_different_reasons_record_different_reasons(reg):
    """Two problems can need the same part for unrelated causes, and the
    architecture document has to say which."""
    a = decompose(profile(data_residency="cannot_leave"), reg)
    b = decompose(profile(data_residency="may_leave"), reg)
    assert a.components["governance"].because != b.components["governance"].because


def test_decomposition_is_deterministic(reg):
    p = profile(data_residency="cannot_leave", corpus_size=200000)
    assert decompose(p, reg).components.keys() == decompose(p, reg).components.keys()


# --- predicates ----------------------------------------------------------


def test_a_predicate_naming_an_unknown_dimension_is_reported(reg):
    from fde.predicate import PredicateError, holds

    with pytest.raises(PredicateError, match="no_such_dimension"):
        holds("no_such_dimension == x", Profile(), reg)


def test_a_malformed_predicate_is_reported_rather_than_silently_false(reg):
    """Silently false would drop a component and nobody would notice."""
    from fde.predicate import PredicateError, holds

    with pytest.raises(PredicateError, match="cannot read"):
        holds("corpus_size ~~ 5", Profile(), reg)


def test_comparisons_work_on_numbers(reg):
    from fde.predicate import holds

    assert holds("corpus_size > 1000", profile(corpus_size=200000), reg)
    assert not holds("corpus_size > 1000", profile(corpus_size=10), reg)


def test_equality_works_on_enums(reg):
    from fde.predicate import holds

    assert holds("data_residency == cannot_leave", profile(data_residency="cannot_leave"), reg)


def test_a_predicate_on_something_unknown_is_false_not_an_error(reg):
    """Unknown is a normal state during intake, and must not stop the run."""
    from fde.predicate import holds

    assert not holds("corpus_size > 1000", Profile(), reg)
