"""The space of solutions still standing.

Every fact removes possibilities. A dimension down to one surviving value is
resolved without ever being asked; down to zero is a contradiction, and saying
*which earlier answer* caused it is the difference between a useful error and
a puzzle.
"""

from pathlib import Path

import pytest

from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry
from fde.space import Contradiction, Space

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


@pytest.fixture
def space(reg):
    return Space.from_registry(reg)


# --- starting shape ------------------------------------------------------


def test_the_space_starts_as_everything_the_registry_allows(space):
    assert space.surviving("hosting") == {
        "public-saas", "managed-api", "customer-vpc", "on-prem", "air-gapped",
    }


def test_only_enumerable_dimensions_are_in_the_space(space, reg):
    """A latency budget has no candidate set to prune."""
    assert "latency_budget_ms" not in space.dimensions()
    assert "hosting" in space.dimensions()


def test_nothing_is_resolved_before_anything_is_known(space):
    assert not any(space.resolved(d) for d in space.dimensions())


# --- pruning -------------------------------------------------------------


def test_an_answer_removes_what_it_rules_out(space):
    after = space.answer("data_residency", "cannot_leave")
    assert after.surviving("hosting") == {"customer-vpc", "on-prem", "air-gapped"}


def test_answering_leaves_the_original_untouched(space):
    space.answer("data_residency", "cannot_leave")
    assert "public-saas" in space.surviving("hosting")


def test_answering_one_thing_settles_another_nobody_stated(space):
    """An air gap is a statement about residency too: nothing leaves a network
    with no egress. Nobody says so; it follows."""
    after = space.answer("hosting", "air-gapped")
    assert after.surviving("data_residency") == {"cannot_leave"}


def test_consequences_run_to_a_fixed_point_not_a_single_pass(reg):
    """A collapsed dimension prunes on its own account, which can collapse
    another. Tested against a purpose-built registry so it checks the mechanism
    rather than whatever the shipped content happens to chain today."""
    import textwrap

    from fde.registry import load_registry

    root = _tiny_registry(textwrap.dedent)
    chained = Space.from_registry(load_registry(root))
    after = chained.answer("a", "x")
    assert after.value("b") == "p"      # one hop
    assert after.value("c") == "m"      # two hops, from b collapsing


def test_a_dimension_down_to_one_value_is_resolved_without_being_asked(space):
    after = space.answer("hosting", "air-gapped")
    assert after.resolved("data_residency")
    assert after.value("data_residency") == "cannot_leave"


def test_pruning_is_order_independent(space):
    a = space.answer("data_residency", "cannot_leave").answer("human_waiting", "no")
    b = space.answer("human_waiting", "no").answer("data_residency", "cannot_leave")
    assert a == b


def test_answering_the_same_thing_twice_changes_nothing(space):
    once = space.answer("data_residency", "cannot_leave")
    assert once.answer("data_residency", "cannot_leave") == once


# --- contradiction -------------------------------------------------------


def test_an_impossible_answer_names_the_earlier_one_that_forbids_it(space):
    after = space.answer("data_residency", "cannot_leave")
    with pytest.raises(Contradiction) as exc:
        after.answer("hosting", "public-saas")
    assert "data_residency" in str(exc.value)
    assert "cannot_leave" in str(exc.value)


def test_a_value_the_registry_never_declared_is_rejected_differently(space):
    """A typo is not a contradiction, and saying so saves an argument."""
    with pytest.raises(ValueError, match="not a declared value"):
        space.answer("hosting", "kubernetes-somewhere")


def test_an_unknown_dimension_is_rejected(space):
    with pytest.raises(KeyError):
        space.answer("no_such_dimension", "x")


# --- from a profile ------------------------------------------------------


def test_a_profile_seeds_the_space(space):
    p = Profile()
    p.ingest([Fact("data_residency", "cannot_leave", Provenance.ARTIFACT)])
    assert space.apply(p).surviving("hosting") == {"customer-vpc", "on-prem", "air-gapped"}


def test_a_contested_dimension_does_not_prune(space):
    """Two respondents disagree, so nothing is settled and nothing is removed."""
    p = Profile()
    p.ingest([Fact("hosting", "on-prem", Provenance.INTERVIEW, respondent=_sponsor())])
    p.ingest([Fact("hosting", "managed-api", Provenance.INTERVIEW, respondent=_user())])
    assert space.apply(p).surviving("hosting") == space.surviving("hosting")


def test_facts_outside_the_space_are_ignored_rather_than_crashing(space):
    p = Profile()
    p.ingest([Fact("latency_budget_ms", 200, Provenance.ARTIFACT)])
    assert space.apply(p) == space


# --- bounded work --------------------------------------------------------


def test_exploring_a_dimension_varies_it_alone(space):
    """The combinatorial trap. Holding everything else fixed keeps this linear
    in dimensions x values; enumerating combinations would not terminate."""
    explored = space.explore("hosting")
    assert len(explored) == len(space.surviving("hosting"))
    for candidate in explored:
        assert candidate.resolved("hosting")


def test_exploring_the_whole_space_stays_linear(space):
    total = sum(len(space.explore(d)) for d in space.dimensions())
    assert total <= sum(len(space.surviving(d)) for d in space.dimensions())


def test_exploring_a_resolved_dimension_yields_the_one_case(space):
    after = space.answer("hosting", "air-gapped")
    assert len(after.explore("data_residency")) == 1


def _tiny_registry(dedent):
    """a=x prunes b to one value, which prunes c to one value."""
    import tempfile
    from pathlib import Path

    root = Path(tempfile.mkdtemp()) / "dimensions"
    root.mkdir(parents=True)
    (root / "a.md").write_text(dedent("""\
        ---
        id: a
        type: enum
        values: [x, y]
        prunes: {x: {b: [q]}}
        ---
        """))
    (root / "b.md").write_text(dedent("""\
        ---
        id: b
        type: enum
        values: [p, q]
        prunes: {p: {c: [n]}}
        ---
        """))
    (root / "c.md").write_text(dedent("""\
        ---
        id: c
        type: enum
        values: [m, n]
        ---
        """))
    return root.parent


def _sponsor():
    from fde.models.respondent import Respondent

    return Respondent(role="sponsor", name="A")


def _user():
    from fde.models.respondent import Respondent

    return Respondent(role="user", name="B")
