"""From a decided approach to the code that implements it.

A pattern says *what*; one realization per stack says *how*. That seam exists
because patterns are stable for years and the libraries implementing them churn
in months -- so swapping the library has to change the emitted code and nothing
else about the design.
"""

from pathlib import Path

import pytest

from fde.realization import (
    NoRealization,
    UnsupportedTopology,
    licences_for,
    realization_for,
)
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


# --- every decision can become code --------------------------------------


def test_every_approach_and_component_pair_has_a_pattern(reg):
    """The unit that has to be buildable is the pair, not the approach. An
    approach serving two components needs an implementation for each -- and a
    decision nothing can build fails at emission, which is far too late."""
    realized = {(p.approach, p.component) for p in reg.patterns.values()}
    wanted = {
        (approach.id, component)
        for approach in reg.approaches.values()
        for component in approach.components
    }
    assert wanted <= realized, f"no pattern for: {sorted(wanted - realized)}"


def test_a_decided_approach_resolves_to_a_template(reg):
    chosen = realization_for("deterministic", "representation", reg, topology="air-gapped")
    assert chosen.template


def test_an_approach_with_no_pattern_says_so(reg):
    with pytest.raises(NoRealization, match="imaginary"):
        realization_for("imaginary", "representation", reg, topology="on-prem")


# --- the seam holds ------------------------------------------------------


def test_no_framework_is_always_an_option(reg):
    """Restraint is only available if the option exists. Every pattern carries
    it, and the schema refuses one that does not."""
    for pattern in reg.patterns.values():
        assert "plain-python" in {r.stack for r in pattern.realizations}


def test_every_realization_of_a_pattern_satisfies_one_interface(reg):
    """Otherwise swapping the library changes the architecture rather than the
    code, and the seam is a fiction."""
    for pattern in reg.patterns.values():
        assert len({r.provides for r in pattern.realizations}) == 1


def test_a_realization_names_an_interface_the_registry_declares(reg):
    for pattern in reg.patterns.values():
        for realization in pattern.realizations:
            assert realization.provides in reg.interfaces


# --- topology is a hard filter -------------------------------------------


def test_a_stack_that_cannot_run_air_gapped_is_not_offered_there(reg):
    chosen = realization_for("judged", "evaluation", reg, topology="air-gapped")
    assert "air-gapped" in reg.stacks[chosen.stack].topologies


def test_a_topology_nothing_supports_is_reported_rather_than_fudged(reg):
    with pytest.raises((UnsupportedTopology, NoRealization)):
        realization_for("deterministic", "representation", reg, topology="mainframe")


def test_the_no_framework_realization_runs_anywhere(reg):
    """It is the fallback, so it cannot itself be topology-constrained."""
    plain = reg.stacks["plain-python"]
    assert {"air-gapped", "on-prem", "customer-vpc", "managed"} <= set(plain.topologies)


# --- licences ------------------------------------------------------------


def test_every_stack_declares_a_licence(reg):
    for stack in reg.stacks.values():
        assert stack.licence


def test_the_licences_a_design_drags_in_can_be_listed(reg):
    """An FDE handing a client a project needs to know what came with it,
    before the client's legal team asks."""
    found = licences_for(
        {"representation": "deterministic", "evaluation": "field-match"}, reg, topology="on-prem"
    )
    assert found and all(v for v in found.values())


def test_a_copyleft_stack_is_flagged_rather_than_quietly_included(reg):
    """Handing a proprietary shop an AGPL dependency is a problem created by
    the framework, on the engineer's name."""
    from fde.realization import copyleft

    assert copyleft("AGPL-3.0")
    assert copyleft("GPL-3.0")
    assert not copyleft("Apache-2.0")
    assert not copyleft("MIT")


# --- reuse beats adoption ------------------------------------------------


def test_a_stack_the_client_already_runs_wins_a_tie(reg):
    """Reuse-first. What they already operate beats what we would prefer."""
    chosen = realization_for(
        "vector-search", "retrieval", reg, topology="on-prem", already_running={"pgvector"}
    )
    assert chosen.stack == "pgvector"


def test_reuse_cannot_override_the_topology_filter(reg):
    """Already running it does not make it able to run where it cannot."""
    chosen = realization_for(
        "judged", "evaluation", reg, topology="air-gapped", already_running={"openai-judge"}
    )
    assert chosen.stack != "openai-judge"
