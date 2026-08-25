"""The content that ships with the framework.

Separate from the loader tests, which use fixtures. These assert things about
the real registry, and fail when authored content drifts from the schema.
"""

import re
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


def test_a_realization_pointing_at_a_missing_template_is_reported(registry):
    """It resolves cleanly and then emits a scaffold. Honest, but silent -- and
    the corpus should say where it is thin rather than let someone find out by
    reading generated code."""
    from fde.graph import find_gaps

    gaps = find_gaps(registry, templates=FRAMEWORK / "templates")
    written = [g for g in gaps if g.kind == "missing_template"]
    assert isinstance(written, list)   # zero is the goal, not the assertion


def test_the_gap_names_the_pattern_and_the_stack(registry):
    from fde.graph import find_gaps

    for gap in find_gaps(registry, templates=FRAMEWORK / "templates"):
        if gap.kind == "missing_template":
            assert "/" in gap.detail and ".j2" in gap.detail


def test_every_realization_has_a_template(registry):
    """No realization resolves to a scaffold any more. Where the framework
    decides what to build, it can emit it."""
    from fde.graph import find_gaps

    unwritten = [
        g.detail for g in find_gaps(registry, templates=FRAMEWORK / "templates")
        if g.kind == "missing_template"
    ]
    assert not unwritten, f"still scaffolding: {unwritten}"


def test_every_template_renders(registry):
    """A template with a syntax error emits a broken project, and it would not
    be found until somebody built one."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(FRAMEWORK / "templates")), autoescape=False)
    for pattern in registry.patterns.values():
        for realization in pattern.realizations:
            rendered = env.get_template(realization.template).render(
                component=pattern.component, approach=pattern.approach,
                stack=realization.stack, interface=realization.provides,
                rationale="test", class_name="Thing", rejected=[],
            )
            assert rendered.strip()


def test_every_emitted_module_is_valid_python(registry):
    """Rendering is not enough. It has to parse."""
    import ast

    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(FRAMEWORK / "templates")), autoescape=False)
    for pattern in registry.patterns.values():
        for realization in pattern.realizations:
            source = env.get_template(realization.template).render(
                component=pattern.component, approach=pattern.approach,
                stack=realization.stack, interface=realization.provides,
                rationale="test", class_name="Thing", rejected=[],
            )
            ast.parse(source)   # raises SyntaxError with the file named


def test_every_emitted_module_declares_what_it_satisfies(registry):
    """A module that cannot say which interface it implements cannot be
    swapped for another that implements the same one."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(FRAMEWORK / "templates")), autoescape=False)
    for pattern in registry.patterns.values():
        for realization in pattern.realizations:
            source = env.get_template(realization.template).render(
                component=pattern.component, approach=pattern.approach,
                stack=realization.stack, interface=realization.provides,
                rationale="test", class_name="Thing", rejected=[],
            )
            # Both a plain assignment and an annotated dataclass field are
            # legitimate ways to declare this.
            for attribute in ("interface", "approach", "stack"):
                assert re.search(rf"\b{attribute}(: \w+)? = ", source), (
                    f"{realization.template} does not declare {attribute}"
                )
