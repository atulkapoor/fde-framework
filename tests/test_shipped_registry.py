"""The content that ships with the framework.

Separate from the loader tests, which use fixtures. These assert things about
the real registry, and fail when authored content drifts from the schema.
"""

from pathlib import Path

import pytest

from fde.graph import validate_links
from fde.models.schema import earliest_cap
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def registry():
    return load_registry(FRAMEWORK)


def test_the_shipped_registry_parses_and_cross_links(registry):
    assert not validate_links(registry)


def test_the_component_taxonomy_covers_the_agent_anatomy(registry):
    """Strip the framework names off any agent and these are the parts."""
    assert set(registry.components) >= {
        "perception",
        "memory",
        "planning",
        "reasoning",
        "integration",
        "governance",
        "observability",
    }


def test_memory_is_a_component_in_its_own_right_not_a_kind_of_retrieval(registry):
    """Retrieval reads a corpus someone else wrote. Memory writes what this
    system learned. Different write policy, different failure modes."""
    assert "memory" in registry.components
    assert "memory" not in registry.components["retrieval"].caps


def test_planning_exists_so_it_need_not_be_retrofitted(registry):
    """The component teams skip in a prototype and pay for later."""
    assert "planning" in registry.components


def test_perception_caps_everything_downstream(registry):
    """A badly parsed table is not recovered by a better model."""
    caps = set(registry.components["perception"].caps)
    assert {"retrieval", "reasoning", "memory", "planning"} <= caps


def test_the_cap_graph_is_acyclic(registry):
    """Otherwise 'where do I look first' never terminates."""
    for component in registry.components:
        earliest_cap(component, registry.components)


def test_reasoning_traces_back_to_perception(registry):
    """When an answer is wrong, this is the first place to look."""
    assert earliest_cap("reasoning", registry.components) == "perception"


def test_every_component_says_when_it_is_required(registry):
    """A component with no trigger gets included by habit, and scope doubles."""
    for component in registry.components.values():
        assert component.required_when, f"{component.id} has no required_when"


def test_every_component_carries_prose_explaining_itself(registry):
    """The body is the rationale a person reads. An entry with none is a stub."""
    for component_id in registry.components:
        body = registry.bodies[("components", component_id)]
        assert len(body.strip()) > 100, f"{component_id}: no substantive rationale"
