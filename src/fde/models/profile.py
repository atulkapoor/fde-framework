"""The accumulating answer to "what do we know about this engagement?"

Two rules do all the work here:

1. Arrival order never decides anything. Provenance does, and it is
   dimension-dependent (see `base.wins`). Every fact is kept, so a superseded
   answer stays auditable.

2. Two *people* disagreeing is not a conflict to resolve -- it is a finding to
   report. The dimension is left unresolved and surfaces in the risk section,
   because the gap between what a sponsor believes and what a user experiences
   is usually the most valuable thing discovery produces.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from fde.models.base import Provenance, wins
from fde.models.fact import Fact
from fde.models.respondent import Respondent, Role


class Disagreement(BaseModel):
    """Two respondents gave different answers for the same dimension."""

    dimension: str
    facts: list[Fact]

    @property
    def respondents(self) -> list[Respondent]:
        return [f.respondent for f in self.facts]

    @property
    def values(self) -> list[Any]:
        return [f.value for f in self.facts]

    @property
    def unresolved(self) -> bool:
        return True

    def __str__(self) -> str:  # pragma: no cover - display only
        parts = ", ".join(f"{f.respondent} says {f.value!r}" for f in self.facts)
        return f"{self.dimension}: {parts}"


class Profile:
    """Facts in, resolved values out. Nothing is ever discarded."""

    def __init__(self) -> None:
        self._history: dict[str, list[Fact]] = {}

    def __eq__(self, other: object) -> bool:
        """Same facts in the same order.

        Deliberately stricter than "resolves to the same values": two profiles
        that agree today but hold different evidence are not interchangeable,
        because the next fact to arrive may resolve them differently.
        """
        if not isinstance(other, Profile):
            return NotImplemented
        return self._history == other._history

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        resolved = len(self.values())
        return f"<Profile {resolved} resolved / {len(self._history)} dimensions>"

    # -- writing ----------------------------------------------------------

    def ingest(self, facts: list[Fact]) -> None:
        for fact in facts:
            self._history.setdefault(fact.dimension, []).append(fact)

    # -- reading ----------------------------------------------------------

    def history(self, dimension: str) -> list[Fact]:
        """Every fact ever recorded for this dimension, in arrival order."""
        return list(self._history.get(dimension, []))

    def fact(self, dimension: str) -> Fact | None:
        """The fact that currently holds, or None if unresolved."""
        contenders = self._contenders(dimension)
        return contenders[0] if len(contenders) == 1 else None

    def get(self, dimension: str) -> Any:
        f = self.fact(dimension)
        return f.value if f else None

    def resolved(self, dimension: str) -> bool:
        return self.fact(dimension) is not None

    def values(self) -> dict[str, Any]:
        return {d: self.get(d) for d in self._history if self.resolved(d)}

    def dimensions(self) -> list[str]:
        return list(self._history)

    def is_empty(self) -> bool:
        return not self._history

    def disagreements(self) -> list[Disagreement]:
        out = []
        for dimension in self._history:
            contenders = self._contenders(dimension)
            if len(contenders) > 1:
                out.append(Disagreement(dimension=dimension, facts=contenders))
        return out

    # -- resolution -------------------------------------------------------

    def _contenders(self, dimension: str) -> list[Fact]:
        """The fact(s) that survive provenance ordering.

        One survivor means resolved. More than one means distinct people gave
        distinct answers at the same strength, which is a disagreement.
        """
        facts = self._history.get(dimension)
        if not facts:
            return []

        # Strongest provenance first; anything a stronger fact beats is out.
        surviving: list[Fact] = []
        for candidate in facts:
            if any(wins(other.provenance, candidate.provenance, candidate.kind) for other in facts):
                continue
            surviving.append(candidate)

        # Among equals, a respondent's later answer supersedes their earlier one:
        # people correct themselves, and that is not a disagreement.
        latest_per_source: dict[tuple[Role, str | None, Provenance], Fact] = {}
        for fact in surviving:
            key = (fact.respondent.role, fact.respondent.name, fact.provenance)
            latest_per_source[key] = fact

        distinct = list(latest_per_source.values())
        if len({f.value for f in distinct}) == 1:
            return distinct[:1]
        return distinct
