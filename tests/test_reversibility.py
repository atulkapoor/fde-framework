"""Two structural properties the schema was missing.

**Reversibility.** Some decisions are an afternoon to undo and some are a full
reindex. A framework that treats them alike will spend its confidence in the
wrong place -- and will let an FDE make a one-way choice on a hunch.

**Quality ceilings.** Quality flows one direction. A badly parsed table caps
every stage downstream of it, and no reranker recovers what ingestion threw
away. That ordering decides where to invest and where to look first when
something is wrong.
"""

import pytest
from pydantic import ValidationError

from fde.models.base import Confidence
from fde.models.schema import (
    Component,
    Reversibility,
    Stack,
    confidence_sufficient,
    earliest_cap,
)


def stack(stack_id, **kw):
    return Stack(
        id=stack_id,
        name=stack_id,
        licence="MIT",
        topologies=["on-prem"],
        last_verified="2026-08-21",
        **kw,
    )


# --- reversibility -------------------------------------------------------


def test_a_stack_declares_what_it_costs_to_swap_out():
    assert stack("cohere-rerank", reversibility=Reversibility.CHEAP).reversibility is (
        Reversibility.CHEAP
    )


def test_reversibility_defaults_to_moderate_rather_than_cheap():
    """The safe default. Assuming a decision is easy to undo is how teams
    discover in month four that it is not."""
    assert stack("anything").reversibility is Reversibility.MODERATE


def test_an_embedding_model_is_expensive_because_changing_it_means_a_full_reindex():
    assert stack("bge-m3", reversibility=Reversibility.EXPENSIVE).reversibility is (
        Reversibility.EXPENSIVE
    )


def test_a_reranker_is_cheap_because_it_drops_in_without_a_reindex():
    assert stack("cohere-rerank", reversibility=Reversibility.CHEAP).reversibility is (
        Reversibility.CHEAP
    )


def test_sending_data_to_a_third_party_is_one_way():
    """You cannot un-send it. This is a different category from expensive."""
    s = stack("managed-api", reversibility=Reversibility.ONE_WAY)
    assert s.reversibility is Reversibility.ONE_WAY


# --- confidence must scale with irreversibility --------------------------


def test_a_cheap_decision_may_be_made_on_medium_confidence():
    assert confidence_sufficient(Reversibility.CHEAP, Confidence.MEDIUM)


def test_a_cheap_decision_may_even_be_made_on_low_confidence():
    """Try it; if it is wrong, swap it back this afternoon."""
    assert confidence_sufficient(Reversibility.CHEAP, Confidence.LOW)


def test_an_expensive_decision_needs_more_than_low_confidence():
    assert not confidence_sufficient(Reversibility.EXPENSIVE, Confidence.LOW)


def test_a_one_way_decision_demands_high_confidence():
    assert not confidence_sufficient(Reversibility.ONE_WAY, Confidence.MEDIUM)
    assert confidence_sufficient(Reversibility.ONE_WAY, Confidence.HIGH)


# --- quality ceilings ----------------------------------------------------


def test_a_component_declares_what_it_caps():
    c = Component(id="ingestion", name="Ingestion", caps=["retrieval", "reasoning"])
    assert "retrieval" in c.caps


def test_a_component_cannot_cap_itself():
    with pytest.raises(ValidationError, match="itself"):
        Component(id="ingestion", name="Ingestion", caps=["ingestion"])


def test_the_earliest_capping_component_is_where_to_look_first():
    """A bad answer with bad ingestion is an ingestion problem, whatever the
    reranker is doing."""
    components = {
        "ingestion": Component(id="ingestion", name="I", caps=["retrieval", "reasoning"]),
        "retrieval": Component(id="retrieval", name="R", caps=["reasoning"]),
        "reasoning": Component(id="reasoning", name="G"),
    }
    assert earliest_cap("reasoning", components) == "ingestion"


def test_a_component_nothing_caps_is_its_own_earliest_cause():
    components = {"ingestion": Component(id="ingestion", name="I")}
    assert earliest_cap("ingestion", components) == "ingestion"


def test_cap_cycles_are_rejected_rather_than_looping_forever():
    components = {
        "a": Component(id="a", name="A", caps=["b"]),
        "b": Component(id="b", name="B", caps=["a"]),
    }
    with pytest.raises(ValueError, match="cycle"):
        earliest_cap("a", components)
