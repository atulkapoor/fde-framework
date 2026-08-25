"""Which question to ask, and who to ask it of.

Two ideas do the work.

**Questions are scoped to who can answer them.** You get one meeting with a
sponsor; spending it on workflow detail wastes the only chance to fix success
criteria.

**Order is decided by divergence, not by how much a question prunes.** Pruning
counts eliminated *values*. Divergence measures whether the *outcome* changes.
A dimension can eliminate half the space and change nothing -- do not ask it.
"""

from pathlib import Path

import pytest

from fde.intake.interview import divergence, next_question, remaining_questions
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry
from fde.space import Space

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"
ROLES = ["sponsor", "eval_owner", "user", "admin", "skeptic"]


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


@pytest.fixture
def space(reg):
    return Space.from_registry(reg)


def ids(questions):
    return {q.resolves for q in questions}


@pytest.fixture
def numerics_known(reg, space):
    """Counts and durations already answered.

    Isolates tests about divergence ordering from questions whose divergence
    cannot be scored yet -- those legitimately sort first, which would otherwise
    mask what these tests are checking.
    """
    p = Profile()
    p.ingest(
        [
            Fact(d, 1, Provenance.ARTIFACT)
            for d in reg.dimensions
            if d not in space.dimensions()
        ]
    )
    return p


# --- role scoping --------------------------------------------------------


def test_a_role_is_only_asked_what_it_can_answer(space, reg):
    for role in ROLES:
        for question in remaining_questions(space, Profile(), reg, role=role):
            assert role in question.roles


def test_the_sponsor_and_the_user_are_asked_different_things(space, reg):
    sponsor = ids(remaining_questions(space, Profile(), reg, role="sponsor"))
    user = ids(remaining_questions(space, Profile(), reg, role="user"))
    assert sponsor != user


def test_infrastructure_questions_go_to_the_admin_not_the_sponsor(space, reg):
    """A sponsor guessing at topology is worse than no answer: it arrives with
    interview provenance and outranks nothing, but it wastes the meeting."""
    assert "hosting" in ids(remaining_questions(space, Profile(), reg, role="admin"))
    assert "hosting" not in ids(remaining_questions(space, Profile(), reg, role="sponsor"))


def test_every_dimension_can_be_answered_by_someone(space, reg):
    """A dimension no role owns is a question that never gets asked."""
    askable = set()
    for role in ROLES:
        askable |= ids(remaining_questions(space, Profile(), reg, role=role))
    assert set(space.dimensions()) <= askable


def test_asking_with_no_role_asks_everything_outstanding(space, reg):
    asked = ids(remaining_questions(space, Profile(), reg))
    assert asked == set(reg.dimensions)          # every dimension, not only prunable ones
    assert set(space.dimensions()) < asked        # strictly more than the space holds


# --- what is not asked ---------------------------------------------------


def test_a_dimension_the_prose_settled_is_not_asked_again(space, reg):
    p = Profile()
    p.ingest([Fact("data_residency", "cannot_leave", Provenance.ARTIFACT)])
    assert "data_residency" not in ids(remaining_questions(space.apply(p), p, reg))


def test_a_dimension_that_collapsed_on_its_own_is_never_asked(space, reg):
    """Nobody should be asked where inference runs once egress is ruled out."""
    narrowed = space.answer("hosting", "air-gapped")
    assert "inference" not in ids(remaining_questions(narrowed, Profile(), reg))
    assert "embeddings" not in ids(remaining_questions(narrowed, Profile(), reg))


def test_the_interview_ends_when_nothing_is_left(space, reg, numerics_known):
    settled = space
    for dimension in space.dimensions():
        if not settled.resolved(dimension):
            settled = settled.answer(dimension, sorted(settled.surviving(dimension))[0])
    assert remaining_questions(settled, numerics_known, reg) == []
    assert next_question(settled, numerics_known, reg) is None


# --- divergence ----------------------------------------------------------


def test_divergence_counts_distinct_outcomes_not_eliminated_values(space):
    """The whole distinction, in one assertion."""
    same = divergence("hosting", space, outcome=lambda s: "identical")
    assert same.outcomes == 1
    assert same.considered == len(space.surviving("hosting"))


def test_a_dimension_that_changes_nothing_scores_zero(space):
    assert divergence("hosting", space, outcome=lambda s: "identical").score == 0.0


def test_a_dimension_that_changes_everything_scores_one(space):
    varies = divergence("hosting", space, outcome=lambda s: s.value("hosting"))
    assert varies.score == 1.0


def test_the_next_question_is_the_one_that_changes_the_most(space, reg, numerics_known):
    def outcome(s):
        # Only residency moves this outcome; hosting is noise.
        return s.value("data_residency")

    chosen = next_question(space, numerics_known, reg, outcome=outcome)
    assert chosen.resolves == "data_residency"


def test_a_high_pruning_dimension_that_changes_nothing_is_not_asked_first(
    space, reg, numerics_known
):
    """Hosting prunes more values than anything else and is still the wrong
    question when it does not move the answer."""
    def outcome(s):
        return s.value("human_waiting")

    chosen = next_question(space, numerics_known, reg, outcome=outcome)
    assert chosen.resolves == "human_waiting"


def test_divergence_is_computed_by_exploring_not_by_a_heuristic(space):
    result = divergence("hosting", space, outcome=lambda s: s.value("data_residency"))
    assert result.considered == len(space.surviving("hosting"))
    # air-gapped and on-prem settle residency; the other three leave it open
    assert result.outcomes == 2


def test_exploring_stays_linear_in_the_number_of_dimensions(space, reg):
    """The combinatorial trap, guarded. This must not grow multiplicatively."""
    calls = []

    def outcome(s):
        calls.append(1)
        return None

    remaining_questions(space, Profile(), reg, outcome=outcome)
    budget = sum(len(space.surviving(d)) for d in space.dimensions())
    assert len(calls) <= budget


# --- answering -----------------------------------------------------------


def test_i_do_not_know_is_a_legal_answer_and_does_not_stall(space, reg):
    """An intake that cannot proceed past an unknown is an intake that stops."""
    question = next_question(space, Profile(), reg)
    assert question.skippable


def test_a_question_carries_the_wording_to_say_out_loud(space, reg):
    question = next_question(space, Profile(), reg)
    assert question.asks and question.asks.strip().endswith("?")


# --- dimensions the space cannot hold ------------------------------------


def test_numeric_dimensions_are_asked_even_though_they_cannot_prune(space, reg):
    """How many rows are labelled decides whether supervised approaches exist
    at all. It has no candidate set to prune, and must still be asked."""
    asked = ids(remaining_questions(space, Profile(), reg))
    assert "labelled_count" in asked
    assert "latency_budget_ms" in asked


def test_the_eval_owner_has_something_to_answer(space, reg):
    """The scarcest respondent on an engagement. An interview with nothing to
    ask them is an interview that wastes them."""
    assert ids(remaining_questions(space, Profile(), reg, role="eval_owner"))


def test_a_numeric_dimension_already_known_is_not_asked(space, reg):
    p = Profile()
    p.ingest([Fact("labelled_count", 8000, Provenance.ARTIFACT)])
    assert "labelled_count" not in ids(remaining_questions(space.apply(p), p, reg))


def test_unmeasurable_divergence_is_reported_as_unknown_not_as_zero(space, reg):
    """Zero would mean 'we checked and it does not matter'. Unknown means
    'we cannot check yet'. Conflating them buries the important questions."""
    question = next(
        q for q in remaining_questions(space, Profile(), reg) if q.resolves == "labelled_count"
    )
    assert question.divergence is None


def test_unknown_divergence_outranks_measured_irrelevance(space, reg):
    """A question we cannot score yet beats one we scored and found pointless."""
    ordered = remaining_questions(space, Profile(), reg, outcome=lambda s: "identical")
    assert ordered[0].divergence is None
