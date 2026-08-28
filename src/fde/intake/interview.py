"""Which question to ask, and who to ask it of.

Two ideas do the work here.

**Questions are scoped to who can answer them.** You get one meeting with a
sponsor. Spending it on infrastructure detail wastes the only chance you have to
fix success criteria, and the answer you get will be a guess anyway.

**Order is decided by divergence, not by pruning.** Pruning counts how many
candidate *values* a question eliminates. Divergence measures whether the
*outcome* changes. Those come apart in both directions: a dimension can
eliminate half the space and change nothing, while another eliminates one value
and flips the whole design. Pruning was always a proxy; divergence is the thing
itself.

Divergence takes an `outcome` function rather than hard-coding what an outcome
is. Today that is the settled shape of the space; once decisions exist it
becomes the architecture, and nothing here changes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fde.models.profile import Profile
from fde.registry import Registry
from fde.space import Space

Outcome = Callable[[Space], Any]

# Where an unscoreable question sits in the order: behind anything measured to
# matter, ahead of anything measured not to.
UNKNOWN_DIVERGENCE = 0.5


@dataclass(frozen=True)
class Question:
    resolves: str
    asks: str
    roles: tuple[str, ...]

    # None means "cannot be measured yet", which is not the same as 0.0
    # ("measured, and it changes nothing"). Conflating them buries the
    # important questions behind the ones we happen to be able to score.
    divergence: float | None
    skippable: bool = True  # "I don't know" never stalls an intake

    # Set when another role already answered this: "V. Rao (sponsor) said
    # may_leave". The question is then an invitation to confirm or contest --
    # which is how a disagreement, the most valuable thing discovery
    # produces, can actually happen through the interview.
    contest_of: str | None = None


@dataclass(frozen=True)
class Divergence:
    dimension: str
    considered: int  # how many values were tried
    outcomes: int  # how many distinct results they produced

    @property
    def score(self) -> float:
        """0 when every answer leads to the same place, 1 when all differ."""
        if self.considered <= 1:
            return 0.0
        return (self.outcomes - 1) / (self.considered - 1)


def default_outcome(space: Space) -> Any:
    """What a question settles, absent a real decision engine.

    Deliberately the *resolved* shape rather than the surviving sets: two answers
    that leave different options open but settle the same things are, for the
    purpose of choosing a question, the same answer.
    """
    return tuple(sorted((d, space.value(d)) for d in space.dimensions() if space.resolved(d)))


def divergence(dimension: str, space: Space, outcome: Outcome = default_outcome) -> Divergence:
    """How much this dimension's answer changes where you end up."""
    explored = space.explore(dimension)
    return Divergence(
        dimension=dimension,
        considered=len(explored),
        outcomes=len({_hashable(outcome(candidate)) for candidate in explored}),
    )


def remaining_questions(
    space: Space,
    profile: Profile,
    registry: Registry,
    role: str | None = None,
    outcome: Outcome = default_outcome,
    scope: str | None = None,
) -> list[Question]:
    """Everything still worth asking, most decisive first.

    A dimension already resolved is never asked -- including one that resolved
    on its own, because nobody should be asked where inference runs once egress
    has been ruled out.
    """
    questions = []
    for dimension, entry in registry.dimensions.items():
        if scope and str(entry.scope) != scope:
            continue
        # Enumerable dimensions live in the space and may already be settled,
        # including by a cascade nobody stated. Everything else -- counts,
        # durations, booleans -- has no candidate set to prune but still has to
        # be asked: how many rows are labelled decides whether supervised
        # approaches exist at all.
        if dimension in space.dimensions():
            if space.resolved(dimension):
                continue
            score = divergence(dimension, space, outcome).score
        else:
            if profile.resolved(dimension):
                continue
            score = None

        roles = tuple(entry.ask_role)
        if role and role not in roles:
            continue
        questions.append(
            Question(
                resolves=dimension,
                asks=entry.asks or f"What is {dimension}?",
                roles=roles,
                divergence=score,
            )
        )

    # Unknown sits between the two things we do know: below a question measured
    # to change the answer, above one measured to change nothing. Treating it as
    # maximum would put every unscoreable question ahead of the decisive ones.
    #
    # The explicit None check matters -- `q.divergence or UNKNOWN` would treat a
    # measured 0.0 as unknown, which is the opposite of what it means.
    ordered = sorted(
        questions,
        key=lambda q: (-(UNKNOWN_DIVERGENCE if q.divergence is None else q.divergence),
                       q.resolves),
    )

    # After the open questions: what another role already settled, offered to
    # this one to confirm or contest. Without this, the first answer retired
    # the question for everyone -- and a second respondent could never
    # disagree through the interview, making the disagreement machinery
    # unreachable by the tool built to feed it. Only claims a differing
    # answer could actually register against are offered: contesting a
    # measurement or a document is futile, and futile questions waste the
    # one meeting you get.
    if role:
        ordered.extend(
            q for q in _contestable(profile, registry, role)
            if not scope or str(registry.dimensions[q.resolves].scope) == scope
        )
    return ordered


def _contestable(profile: Profile, registry: Registry, role: str) -> list[Question]:
    from fde.models.base import Provenance

    questions = []
    for dimension, entry in registry.dimensions.items():
        if role not in entry.ask_role:
            continue
        if not profile.resolved(dimension):
            continue
        fact = profile.fact(dimension)
        if fact is None or fact.provenance not in (
            Provenance.INTERVIEW, Provenance.INFERRED,
        ):
            continue
        holder = str(fact.respondent.role)
        if holder == role:
            continue
        who = fact.respondent.name or holder
        questions.append(
            Question(
                resolves=dimension,
                asks=entry.asks or f"What is {dimension}?",
                roles=tuple(entry.ask_role),
                divergence=None,
                contest_of=f"{who} ({holder}) said {fact.value}",
            )
        )
    return sorted(questions, key=lambda q: q.resolves)


def next_question(
    space: Space,
    profile: Profile,
    registry: Registry,
    role: str | None = None,
    outcome: Outcome = default_outcome,
) -> Question | None:
    questions = remaining_questions(space, profile, registry, role=role, outcome=outcome)
    return questions[0] if questions else None


def _hashable(value: Any) -> Any:
    """Outcomes are supplied by callers and need only be comparable."""
    try:
        hash(value)
        return value
    except TypeError:  # pragma: no cover - defensive
        return repr(value)
