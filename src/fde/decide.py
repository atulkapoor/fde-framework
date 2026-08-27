"""What to build for each component, and why.

Three rules carry this, and they matter more than the selection mechanism.

**The simplest applicable approach wins.** `complexity` orders candidates by
cost of ownership, not capability. A framework that reaches for the most capable
option available is the failure this exists to prevent -- and the one that makes
an engagement expensive to hand over.

**Every decision names what it rejected and why.** A recommendation with no
rejected alternatives has not been made, it has been assumed. It is also the
half a client actually reads, because it tells them what they are not getting.

**Nothing known means nothing decided.** No default, no "probably". The gates
report the gap and the interview asks.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from fde.models.base import Confidence, Evidence
from fde.models.profile import Profile
from fde.models.schema import Approach, Reversibility, confidence_sufficient
from fde.predicate import holds
from fde.predicate import referenced as _referenced
from fde.registry import Registry


@dataclass(frozen=True)
class Rejected:
    id: str
    reason: str


@dataclass
class Decision:
    component: str
    approach: str | None
    rationale: str
    rejected: list[Rejected] = field(default_factory=list)
    evidence: Evidence | None = None
    confidence: Confidence = Confidence.MEDIUM
    reversibility: Reversibility = Reversibility.MODERATE

    # How many approaches were on the table at all. One is not the same as
    # "we weighed the options and this won" -- it means the registry offers no
    # alternative, which a client should be told rather than left to assume.
    considered: int = 0

    @property
    def uncontested(self) -> bool:
        return self.considered == 1

    def as_tuple(self) -> tuple:
        return (self.component, self.approach)


class Decisions(dict):
    """Component id -> Decision, with a stable identity for the whole set."""

    def undecided(self) -> list[str]:
        """Components in scope that nothing can currently fill."""
        return sorted(c for c, d in self.items() if not d.approach)

    def decided(self) -> Decisions:
        return Decisions({c: d for c, d in self.items() if d.approach})

    def decided_fingerprint(self) -> str:
        return self.decided().fingerprint()

    def fingerprint(self) -> str:
        """One value standing for the whole architecture.

        This is what divergence compares: does answering a question change what
        gets built? Built from the decisions themselves rather than from the
        profile, so two different profiles that lead to the same design are
        correctly treated as the same answer.
        """
        payload = json.dumps(
            sorted(d.as_tuple() for d in self.values() if d.approach), separators=(",", ":")
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def decide_component(
    component: str, values: Mapping[str, Any], registry: Registry
) -> Decision | None:
    """Choose an approach for one component, and record what lost."""
    profile = _as_profile(values)

    candidates = [
        a for a in registry.approaches.values() if not a.components or component in a.components
    ]
    if not candidates:
        return None

    applicable: list[Approach] = []
    rejected: list[Rejected] = []
    still_askable: list[Approach] = []

    for approach in candidates:
        blocked = [c for c in approach.avoid_when if holds(c, profile, registry)]
        if blocked:
            rejected.append(
                Rejected(approach.id, f"ruled out by {blocked[0]}")
            )
            continue
        if not any(holds(c, profile, registry) for c in approach.applies_when):
            rejected.append(
                Rejected(approach.id, f"nothing here matches {' or '.join(approach.applies_when)}")
            )
            # Not ruled out -- just not ruled in. If its applies conditions
            # reference something unanswered, an answer could still admit it.
            still_askable.append(approach)
            continue
        applicable.append(approach)

    if not applicable:
        # Two different situations, and telling them apart matters. When the
        # predicates reference things nobody has answered, more discovery is
        # the remedy. When everything was known and every approach is still
        # ruled out, the facts contradict each other -- and reporting that as
        # "not enough is known" sends somebody to ask more questions that
        # cannot help. Name the culprits instead.
        # Only dimensions whose answer could still admit an approach: the
        # applies conditions of candidates that were not ruled out. Collecting
        # from every candidate's every predicate once told a user to go ask
        # four questions none of which could change the outcome -- the exact
        # misdirection this branch exists to prevent.
        unknowns = sorted({
            dimension
            for approach in still_askable
            for condition in approach.applies_when
            for dimension in _referenced(condition)
            if profile.get(dimension) is None
        })
        if unknowns:
            rationale = (
                f"not enough is known to choose -- "
                f"unanswered: {', '.join(unknowns)}"
            )
        else:
            blocked = "; ".join(f"{r.id}: {r.reason}" for r in rejected)
            rationale = (
                f"everything is known and every approach is ruled out -- "
                f"the facts conflict, and asking more questions cannot help. "
                f"{blocked}"
            )
        return Decision(
            component=component,
            approach=None,
            rationale=rationale,
            rejected=rejected,
            considered=len(candidates),
        )

    # Simplest first; among equals, whichever more engagements back.
    applicable.sort(key=lambda a: (a.complexity, -_evidence_count(a), a.id))
    winner, losers = applicable[0], applicable[1:]

    rejected.extend(
        Rejected(a.id, f"{winner.id} is simpler and applies here")
        for a in losers
    )

    evidence = winner.evidence
    confidence = evidence.confidence if evidence else Confidence.LOW
    reversibility = _reversibility(winner)

    if not confidence_sufficient(reversibility, confidence):
        confidence = Confidence.HIGH if reversibility is Reversibility.ONE_WAY else confidence

    rationale = _why(winner, profile, registry)
    if len(candidates) == 1:
        rationale += " -- the only approach registered for this component"

    return Decision(
        component=component,
        approach=winner.id,
        rationale=rationale,
        rejected=rejected,
        evidence=evidence,
        confidence=confidence,
        reversibility=reversibility,
        considered=len(candidates),
    )


def decide_all(
    values: Mapping[str, Any], registry: Registry, components: list[str] | None = None
) -> Decisions:
    """Decide every component asked for -- including the ones we cannot.

    A component decomposition put in scope but decision cannot fill does not
    disappear. It stays, with no approach and a rationale saying why, because a
    component that vanishes between "you need this" and "here is the design" is
    a hole nobody notices until build time.
    """
    wanted = components if components is not None else list(registry.components)
    decisions = Decisions()
    for component in wanted:
        decision = decide_component(component, values, registry)
        if decision is None:
            decision = Decision(
                component=component,
                approach=None,
                rationale="no approach in the registry serves this component",
                considered=0,
            )
        decisions[component] = decision
    return decisions


def architecture_outcome(registry: Registry, components: list[str] | None = None):
    """An outcome function for divergence: what actually gets built.

    The placeholder measured which dimensions got settled. This measures the
    design, which is the question worth asking -- a question that narrows the
    space but changes nothing is not worth a client's time.
    """

    def outcome(space) -> str:
        values = {d: space.value(d) for d in space.dimensions() if space.resolved(d)}
        return decide_all(values, registry, components=components).fingerprint()

    return outcome


# --- helpers -------------------------------------------------------------


def _as_profile(values: Mapping[str, Any]) -> Profile:
    """Decisions are made from resolved values, whether those came from a
    profile or from exploring a hypothetical."""
    if isinstance(values, Profile):
        return values

    from fde.models.base import Provenance
    from fde.models.fact import Fact

    profile = Profile()
    profile.ingest(
        [Fact(k, v, Provenance.ARTIFACT) for k, v in values.items() if v is not None]
    )
    return profile


def _evidence_count(approach: Approach) -> int:
    return len(approach.evidence.case_ids) if approach.evidence else 0


def _reversibility(approach: Approach) -> Reversibility:
    # Adapting weights means retraining and re-evaluating to undo.
    return Reversibility.EXPENSIVE if approach.id == "finetune" else Reversibility.MODERATE


def _why(approach: Approach, profile: Profile, registry: Registry) -> str:
    fired = [c for c in approach.applies_when if holds(c, profile, registry)]
    return f"{approach.name}: {'; '.join(fired)}"
