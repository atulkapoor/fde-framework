"""How the model gets served -- and making the dimensions that decide it matter.

Divergence reported that hosting, residency, inference and human_waiting all
changed nothing about the architecture. They obviously should. That was not a
mechanism failure; it was the corpus telling us it had nothing to say about
them, which is the more useful kind of finding.
"""

from pathlib import Path

import pytest

from fde.decide import architecture_outcome, decide_component
from fde.graph import find_gaps
from fde.intake.interview import divergence
from fde.registry import load_registry
from fde.space import Space

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def serving(reg, **values):
    return decide_component("serving", values, reg)


# --- the sensitivity driver ----------------------------------------------


def test_data_that_cannot_leave_is_never_served_by_a_vendor_api(reg):
    decision = serving(reg, output_shape="freeform", data_residency="cannot_leave")
    assert decision.approach != "managed-api"


def test_data_that_may_leave_takes_the_simplest_thing(reg):
    """Managed is the cheapest way to be wrong cheaply. Earn past it."""
    decision = serving(reg, output_shape="freeform", data_residency="may_leave",
                       human_waiting="yes")
    assert decision.approach == "managed-api"


def test_an_air_gap_rules_out_calling_anything(reg):
    decision = serving(reg, output_shape="freeform", hosting="air-gapped")
    assert decision.approach == "self-hosted"
    assert "managed-api" in {r.id for r in decision.rejected}


# --- the economics driver ------------------------------------------------


def test_high_volume_batch_prefers_scale_to_zero_over_per_token_pricing(reg):
    """Cold start is a user-experience problem only when someone is waiting,
    and at volume per-token pricing runs several times what rented GPUs cost."""
    decision = serving(reg, output_shape="freeform", human_waiting="no",
                       data_residency="may_leave", corpus_size=200_000)
    assert decision.approach == "serverless-gpu"


def test_low_volume_batch_still_takes_the_simpler_thing(reg):
    """Nobody waiting is not on its own a reason to run infrastructure. It is
    volume that makes per-token pricing lose, and a small job never gets there."""
    decision = serving(reg, output_shape="freeform", human_waiting="no",
                       data_residency="may_leave", corpus_size=500)
    assert decision.approach == "managed-api"


def test_someone_waiting_does_not_get_a_cold_start(reg):
    decision = serving(reg, output_shape="freeform", human_waiting="yes",
                       data_residency="may_leave")
    assert decision.approach != "serverless-gpu"


def test_the_two_drivers_are_independent(reg):
    """Sensitivity partitions by what; economics partitions by when. A batch
    job on data that cannot leave is still self-hosted."""
    decision = serving(reg, output_shape="freeform", human_waiting="no",
                       data_residency="cannot_leave")
    assert decision.approach == "self-hosted"


# --- the dimensions now move the design ----------------------------------


def test_residency_now_changes_the_architecture(reg):
    space = Space.from_registry(reg).answer("output_shape", "freeform")
    assert divergence("data_residency", space, outcome=architecture_outcome(reg)).score > 0


def test_whether_someone_is_waiting_now_changes_the_architecture(reg):
    space = Space.from_registry(reg).answer("output_shape", "freeform")
    assert divergence("human_waiting", space, outcome=architecture_outcome(reg)).score > 0


def test_hosting_now_changes_the_architecture(reg):
    space = Space.from_registry(reg).answer("output_shape", "freeform")
    assert divergence("hosting", space, outcome=architecture_outcome(reg)).score > 0


# --- a dimension nothing acts on is a gap --------------------------------


def test_a_dimension_no_decision_depends_on_is_reported_as_a_gap(reg):
    """Asking a question whose answer changes nothing wastes the one meeting
    you get. Gap detection should catch that, not just missing entries."""
    kinds = {g.kind for g in find_gaps(reg)}
    assert "inert_dimension" in kinds or _all_dimensions_act(reg)


def _all_dimensions_act(reg) -> bool:
    referenced = set()
    for approach in reg.approaches.values():
        for condition in [*approach.applies_when, *approach.avoid_when]:
            referenced.add(condition.split()[0])
    for component in reg.components.values():
        for condition in component.required_when:
            referenced.add(condition.split()[0])
    return set(reg.dimensions) <= referenced
