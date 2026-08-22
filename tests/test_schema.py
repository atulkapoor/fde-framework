"""The shapes registry content must satisfy.

These are authored before any content, deliberately: authoring against an
undefined schema guarantees a rewrite.
"""

import pytest
from pydantic import ValidationError

from fde.models.base import DimensionKind
from fde.models.schema import (
    Approach,
    Dimension,
    Ladder,
    Pattern,
    Realization,
    Rung,
    Stack,
    ValueType,
)

# --- dimensions ----------------------------------------------------------


def test_a_dimension_declares_a_value_type():
    """This is what makes a vague answer a parse failure rather than a judgement.
    'fast' is not a duration_ms, and no model is needed to know that."""
    d = Dimension(id="latency_budget_ms", type=ValueType.DURATION_MS)
    assert d.type is ValueType.DURATION_MS


def test_an_enum_dimension_must_enumerate_its_values():
    with pytest.raises(ValidationError, match="values"):
        Dimension(id="hosting", type=ValueType.ENUM)


def test_a_non_enum_dimension_must_not_enumerate_values():
    with pytest.raises(ValidationError):
        Dimension(id="peak_qps", type=ValueType.COUNT, values=["a", "b"])


def test_dimension_kind_defaults_to_requirement():
    """You cannot detect a latency budget, only a latency."""
    assert Dimension(id="latency_budget_ms", type=ValueType.DURATION_MS).kind is (
        DimensionKind.REQUIREMENT
    )


def test_an_option_may_prune_values_from_other_dimensions():
    d = Dimension(
        id="data_residency",
        type=ValueType.ENUM,
        values=["cannot_leave", "may_leave"],
        prunes={"cannot_leave": {"hosting": ["public-saas", "managed-api"]}},
    )
    assert d.prunes["cannot_leave"]["hosting"] == ["public-saas", "managed-api"]


def test_pruning_may_only_reference_values_the_dimension_declares():
    with pytest.raises(ValidationError, match="undeclared value"):
        Dimension(
            id="data_residency",
            type=ValueType.ENUM,
            values=["cannot_leave"],
            prunes={"maybe": {"hosting": ["public-saas"]}},
        )


def test_the_inference_split_dimensions_are_expressible():
    """Two independent reasons to split a path: when (latency) and what
    (sensitivity). Both must be representable, and they co-occur."""
    when = Dimension(id="human_waiting", type=ValueType.ENUM, values=["yes", "no", "mixed"])
    what = Dimension(
        id="sensitivity_split",
        type=ValueType.ENUM,
        values=["none", "by_record", "by_field", "by_stage"],
    )
    assert "mixed" in when.values and "by_field" in what.values


def test_unclassifiable_policy_admits_only_the_restrictive_value():
    """Fail closed. An unclassifiable record takes the restrictive path, always."""
    d = Dimension(id="unclassifiable_policy", type=ValueType.ENUM, values=["restrictive"])
    assert d.values == ["restrictive"]


# --- stacks --------------------------------------------------------------


def test_a_stack_declares_licence_topologies_and_when_it_was_last_checked():
    s = Stack(
        id="pgvector",
        name="pgvector",
        licence="PostgreSQL",
        topologies=["customer-vpc", "on-prem", "air-gapped"],
        last_verified="2026-08-21",
    )
    assert s.licence and s.topologies and s.last_verified


def test_a_stack_with_no_topology_is_rejected():
    """A tool that cannot be placed anywhere cannot be recommended."""
    with pytest.raises(ValidationError):
        Stack(id="x", name="X", licence="MIT", topologies=[], last_verified="2026-08-21")


def test_capability_maturity_is_constrained_not_free_text():
    s = Stack(
        id="pgvector",
        name="pgvector",
        licence="PostgreSQL",
        topologies=["on-prem"],
        last_verified="2026-08-21",
        provides={"vector_search": "stable"},
    )
    assert s.provides["vector_search"] == "stable"
    with pytest.raises(ValidationError):
        Stack(
            id="x",
            name="X",
            licence="MIT",
            topologies=["on-prem"],
            last_verified="2026-08-21",
            provides={"vector_search": "pretty good"},
        )


# --- patterns and realizations -------------------------------------------


def test_a_pattern_carries_one_realization_per_stack():
    """Patterns are stable for years; the libraries implementing them churn
    in months. That seam is the whole point of separating them."""
    p = Pattern(
        id="supervisor-worker",
        component="orchestration",
        realizations=[
            Realization(stack="langgraph", template="supervisor/langgraph.py.j2",
                        provides="Supervisor"),
            Realization(stack="google-adk", template="supervisor/adk.py.j2",
                        provides="Supervisor"),
            Realization(stack="plain-python", template="supervisor/plain.py.j2",
                        provides="Supervisor"),
        ],
    )
    assert {r.stack for r in p.realizations} == {"langgraph", "google-adk", "plain-python"}


def test_every_realization_of_a_pattern_satisfies_the_same_interface():
    """Otherwise swapping the stack would change the architecture, not just the code."""
    with pytest.raises(ValidationError, match="same interface"):
        Pattern(
            id="supervisor-worker",
            component="orchestration",
            realizations=[
                Realization(stack="langgraph", template="a.j2", provides="Supervisor"),
                Realization(stack="google-adk", template="b.j2", provides="Retriever"),
            ],
        )


def test_a_pattern_must_offer_a_no_framework_realization():
    """Restraint versus craft is only real if the framework can say
    'you do not need LangGraph for this'."""
    with pytest.raises(ValidationError, match="plain-python"):
        Pattern(
            id="supervisor-worker",
            component="orchestration",
            realizations=[
                Realization(stack="langgraph", template="a.j2", provides="Supervisor")
            ],
        )


def test_a_pattern_with_no_realization_cannot_exist():
    with pytest.raises(ValidationError):
        Pattern(id="x", component="orchestration", realizations=[])


# --- approaches ----------------------------------------------------------


def test_an_approach_states_when_to_avoid_it_not_only_when_to_use_it():
    """An approach with no avoid_when has never been thought about properly."""
    with pytest.raises(ValidationError, match="avoid_when"):
        Approach(id="graph-retrieval", name="Graph retrieval", applies_when=["multi-hop"])


def test_graph_retrieval_is_expressible_as_an_approach():
    """It loses to plain chunks on simple fact retrieval, which is exactly the
    kind of thing avoid_when exists to record."""
    a = Approach(
        id="graph-retrieval",
        name="Graph retrieval",
        applies_when=["multi-hop reasoning is a measured share of query traffic"],
        avoid_when=[
            "single-fact lookup dominates",
            "the corpus churns often",
            "the latency budget cannot absorb 2-3x",
        ],
    )
    assert len(a.avoid_when) == 3


# --- ladders -------------------------------------------------------------


def test_every_rung_but_the_last_declares_how_to_earn_the_next():
    """graduate_when is the most important field in the schema. A ladder without
    it is a list of options, and the framework defaults to the fanciest."""
    with pytest.raises(ValidationError, match="graduate_when"):
        Ladder(
            id="autonomy",
            rungs=[Rung(n=0, id="gate-everything"), Rung(n=1, id="gate-mutative")],
        )


def test_the_final_rung_needs_no_graduation():
    ladder = Ladder(
        id="autonomy",
        rungs=[
            Rung(n=0, id="gate-everything", graduate_when="unedited_approval_rate > 0.9"),
            Rung(n=1, id="gate-mutative"),
        ],
    )
    assert ladder.rungs[-1].graduate_when is None


def test_rungs_must_be_contiguous_from_zero():
    with pytest.raises(ValidationError, match="contiguous"):
        Ladder(id="autonomy", rungs=[Rung(n=1, id="a"), Rung(n=3, id="b")])


def test_a_ladder_starts_at_the_cheapest_rung():
    """Earn your way rightward."""
    ladder = Ladder(
        id="deployment-substrate",
        rungs=[
            Rung(n=0, id="systemd", graduate_when="more than one long-lived process"),
            Rung(n=1, id="compose", graduate_when="multi-node scheduling required"),
            Rung(n=2, id="kubernetes"),
        ],
    )
    assert ladder.rungs[0].id == "systemd"
