"""What an answer would change.

The interview already orders questions by divergence: how many distinct
places the surviving answers lead. This makes the divergence legible for
one question -- the evidence the record already holds on that dimension,
each candidate answer, and the components whose approach would differ --
so the question is asked knowing what hangs on it. Every candidate is
tried as the framework's own guess and never written to the record.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from fde.architect import architect as build_architecture
from fde.models.base import Provenance
from fde.models.fact import Fact


@dataclass
class Impact:
    dimension: str
    evidence: list[str] = field(default_factory=list)
    outcomes: list[tuple[Any, dict[str, str | None]]] = field(default_factory=list)
    explorable: bool = True

    @property
    def differing(self) -> list[str]:
        components = sorted({c for _, decided in self.outcomes for c in decided})
        return [c for c in components
                if len({decided.get(c) for _, decided in self.outcomes}) > 1]


def decision_impact(dimension: str, profile, registry, space) -> Impact:
    impact = Impact(dimension)
    for fact in profile.history(dimension):
        impact.evidence.append(f"{fact.respondent} said {fact.value} [{fact.provenance.value}]")
    if dimension not in space.dimensions():
        impact.explorable = False
        return impact
    for candidate in space.explore(dimension):
        value = candidate.value(dimension)
        trial = copy.deepcopy(profile)
        trial.ingest([Fact(dimension, value, Provenance.INFERRED)])
        decided = {component: decision.approach
                   for component, decision in build_architecture(trial, registry)
                   .decisions.items()}
        impact.outcomes.append((value, decided))
    return impact


def render_impact(impact: Impact) -> str:
    lines = []
    if impact.evidence:
        lines.append(f"  evidence on {impact.dimension}:")
        lines += [f"    {line}" for line in impact.evidence]
    else:
        lines.append(f"  evidence on {impact.dimension}: nothing recorded")
    if not impact.explorable:
        lines.append("  impact: not an enumerable dimension; the answer decides which "
                     "approaches exist at all rather than which is chosen")
        return "\n".join(lines)
    differing = impact.differing
    if not differing:
        lines.append(f"  impact: {len(impact.outcomes)} answer(s) explored; none changes a "
                     "decision yet -- the answer narrows the space, not the build")
        return "\n".join(lines)
    lines.append(f"  impact: {len(impact.outcomes)} answer(s) explored; "
                 f"{len(differing)} decision(s) turn on it")
    for value, decided in impact.outcomes:
        shown = ", ".join(f"{c}: {decided.get(c) or 'undecided'}" for c in differing)
        lines.append(f"    {value!s:24} -> {shown}")
    return "\n".join(lines)
