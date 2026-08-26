"""The four engagement moves, as graph transformations.

Each is a pure function from graph to graph. That matters for two reasons: they
can be applied in any order without arguing about precedence, and applying one
twice cannot double up the gates it inserts.

The moves are where judgement that would otherwise live in an FDE's head becomes
something the build can check.
"""

from pathlib import Path

import pytest

from fde.decide import decide_all
from fde.decompose import decompose
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.moves import BoundaryViolation, apply_move, assert_boundary
from fde.registry import load_registry
from fde.workflow import build_graph

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"

SENSITIVE = dict(
    output_shape="freeform", data_residency="cannot_leave", hosting="air-gapped",
    corpus_size=200_000, latency_budget_ms=800,
)
OPEN = dict(
    output_shape="freeform", data_residency="may_leave", human_waiting="yes",
    corpus_size=500, latency_budget_ms=800,
)
SIMPLE = dict(output_shape="structured", corpus_size=100)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def graph_for(reg, values):
    profile = Profile()
    profile.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    components = decompose(profile, reg)
    return build_graph(
        decide_all(values, reg, components=list(components.components)),
        reg,
        values=values,
    )


# --- the graph itself ----------------------------------------------------


def test_every_decided_component_becomes_a_node(reg):
    graph = graph_for(reg, SENSITIVE)
    assert graph.nodes


def test_nodes_are_ordered_by_what_caps_what(reg):
    """Perception feeds everything downstream, so it cannot come second."""
    graph = graph_for(reg, SENSITIVE)
    order = [n.id for n in graph.ordered()]
    assert order.index("perception") < order.index("reasoning")


def test_a_node_that_touches_the_world_is_marked_mutative(reg):
    graph = graph_for(reg, dict(output_shape="decision", latency_budget_ms=200))
    assert any(n.mutative for n in graph.nodes.values())


# --- move 1: autonomy against safety -------------------------------------


def test_an_approval_gate_precedes_every_mutative_step(reg):
    graph = apply_move(graph_for(reg, dict(output_shape="decision", latency_budget_ms=200)),
                       "autonomy-vs-safety")
    for node in graph.mutative_nodes():
        assert any(p.type == "ApprovalGate" for p in graph.predecessors(node.id))


def test_mutative_steps_carry_an_idempotency_key(reg):
    """Structural impossibility beats testing. A double-charge cannot happen,
    rather than being something we wrote a test for."""
    graph = apply_move(graph_for(reg, dict(output_shape="decision", latency_budget_ms=200)),
                       "autonomy-vs-safety")
    assert all(n.idempotency_key for n in graph.mutative_nodes())


def test_nothing_is_gated_when_nothing_mutates(reg):
    """The move must not add ceremony to a read-only pipeline."""
    before = graph_for(reg, SIMPLE)
    after = apply_move(before, "autonomy-vs-safety")
    assert len(after.nodes) == len(before.nodes)


# --- move 2: restraint against craft -------------------------------------


def test_the_simple_path_is_left_alone(reg):
    """A move that only ever adds is not a move, it is a habit."""
    before = graph_for(reg, SIMPLE)
    after = apply_move(before, "restraint-vs-craft")
    assert len(after.nodes) <= len(before.nodes)


def test_restraint_reports_what_it_removed(reg):
    after = apply_move(graph_for(reg, SIMPLE), "restraint-vs-craft")
    assert after.notes is not None


# --- move 3: data cannot leave -------------------------------------------


def test_a_boundary_split_appears_when_data_cannot_leave(reg):
    graph = apply_move(graph_for(reg, SENSITIVE), "data-cannot-leave")
    assert graph.has_type("BoundarySplit")


def test_no_boundary_split_when_nothing_forbids_egress(reg):
    graph = apply_move(graph_for(reg, OPEN), "data-cannot-leave")
    assert not graph.has_type("BoundarySplit")


def test_sensitive_work_is_pinned_inside(reg):
    graph = apply_move(graph_for(reg, SENSITIVE), "data-cannot-leave")
    assert all(graph.placement[n.id] == "in_boundary" for n in graph.sensitive_nodes())


def test_the_boundary_is_asserted_not_merely_intended(reg):
    graph = apply_move(graph_for(reg, SENSITIVE), "data-cannot-leave")
    assert_boundary(graph)  # raises if anything sensitive sits outside


def test_a_sensitive_node_outside_the_boundary_fails_the_build(reg):
    """Not a warning. A leak that only produces a warning is a leak."""
    graph = apply_move(graph_for(reg, SENSITIVE), "data-cannot-leave")
    leaking = next(iter(graph.sensitive_nodes()))
    graph.placement[leaking.id] = "external"
    with pytest.raises(BoundaryViolation, match=leaking.id):
        assert_boundary(graph)


def test_an_embedding_of_sensitive_data_is_itself_sensitive(reg):
    """'We only send vectors, not text' is not a defence -- an embedding is
    recoverable to its source."""
    graph = apply_move(graph_for(reg, SENSITIVE), "data-cannot-leave")
    representation = graph.nodes.get("representation")
    if representation:
        assert graph.placement["representation"] == "in_boundary"


# --- move 4: failure into leverage ---------------------------------------


def test_a_critic_precedes_anything_irreversible(reg):
    graph = apply_move(graph_for(reg, dict(output_shape="decision", latency_budget_ms=200)),
                       "failure-to-leverage")
    for node in graph.irreversible_nodes():
        assert any(p.type == "Critic" for p in graph.predecessors(node.id))


# --- the properties that make them composable ----------------------------


@pytest.mark.parametrize(
    "move",
    ["autonomy-vs-safety", "restraint-vs-craft", "data-cannot-leave", "failure-to-leverage"],
)
def test_applying_a_move_twice_changes_nothing_the_second_time(reg, move):
    once = apply_move(graph_for(reg, SENSITIVE), move)
    assert apply_move(once, move) == once


def test_the_order_moves_are_applied_in_does_not_matter(reg):
    base = graph_for(reg, SENSITIVE)
    forward = apply_move(apply_move(base, "autonomy-vs-safety"), "data-cannot-leave")
    backward = apply_move(apply_move(base, "data-cannot-leave"), "autonomy-vs-safety")
    assert forward == backward


def test_an_unknown_move_is_refused(reg):
    with pytest.raises(KeyError):
        apply_move(graph_for(reg, SIMPLE), "wishful-thinking")


# --- nothing disappears quietly ------------------------------------------


def test_a_component_nothing_can_fill_still_appears_in_the_graph(reg):
    """Decomposition said it was needed. If decision cannot fill it, that is a
    hole to be seen, not a component to drop."""
    graph = graph_for(reg, dict(output_shape="decision", latency_budget_ms=200))
    assert "integration" in graph.nodes
    assert graph.nodes["integration"].unfilled


def test_unfilled_components_are_listed_so_they_can_be_answered_for(reg):
    from fde.decide import decide_all as decide

    decisions = decide(dict(output_shape="decision", latency_budget_ms=200), reg)
    assert "integration" in decisions.undecided()
