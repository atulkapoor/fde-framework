"""The space of solutions still standing.

Every fact removes possibilities. Two consequences matter more than the
mechanism:

**A dimension down to one value is resolved without being asked.** Nobody has to
state that an air-gapped deployment self-hosts its inference; it is the only
thing left. Questions the answers already settled are never put to a client.

**A dimension down to zero is a contradiction**, and the error names the earlier
answer responsible. "No valid configuration" is a puzzle; "you said data cannot
leave, which rules out a public SaaS" is an answer.

Spaces are immutable. Answering returns a new one, so exploring what an answer
*would* do costs nothing and cannot corrupt what is known.
"""

from __future__ import annotations

from fde.models.profile import Profile
from fde.models.schema import ValueType
from fde.registry import Registry


class Contradiction(Exception):
    """An answer that nothing left in the space can satisfy."""


class Space:
    def __init__(
        self,
        surviving: dict[str, set[str]],
        registry: Registry,
        answered: list[tuple[str, str]] | None = None,
    ) -> None:
        self._surviving = surviving
        self._registry = registry
        self._answered = answered or []

    # -- construction -----------------------------------------------------

    @classmethod
    def from_registry(cls, registry: Registry) -> Space:
        """Everything the registry allows, before anything is known.

        Only enumerable dimensions take part: a latency budget is a number, and
        there is no candidate set to prune.
        """
        surviving = {
            d.id: set(d.values)
            for d in registry.dimensions.values()
            if d.type is ValueType.ENUM and d.values
        }
        return cls(surviving, registry)

    # -- reading ----------------------------------------------------------

    def dimensions(self) -> list[str]:
        return sorted(self._surviving)

    def surviving(self, dimension: str) -> set[str]:
        return set(self._surviving[dimension])

    def resolved(self, dimension: str) -> bool:
        return len(self._surviving.get(dimension, ())) == 1

    def value(self, dimension: str) -> str | None:
        candidates = self._surviving.get(dimension, set())
        return next(iter(candidates)) if len(candidates) == 1 else None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Space):
            return NotImplemented
        return self._surviving == other._surviving

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        resolved = sum(1 for d in self._surviving if self.resolved(d))
        return f"<Space {resolved}/{len(self._surviving)} resolved>"

    # -- narrowing --------------------------------------------------------

    def answer(self, dimension: str, value: str) -> Space:
        """Fix a dimension and propagate everything that follows."""
        if dimension not in self._surviving:
            raise KeyError(f"{dimension!r} is not a dimension in this space")

        declared = set(self._registry.dimensions[dimension].values)
        if value not in declared:
            raise ValueError(
                f"{value!r} is not a declared value for {dimension!r}. "
                f"Expected one of: {', '.join(sorted(declared))}"
            )

        if value not in self._surviving[dimension]:
            raise Contradiction(
                f"{dimension}={value} is ruled out by {self._blame(dimension, value)}"
            )

        narrowed = dict(self._surviving)
        narrowed[dimension] = {value}
        return Space(
            self._settle(narrowed), self._registry, [*self._answered, (dimension, value)]
        )

    def apply(self, profile: Profile) -> Space:
        """Seed from what is already known.

        A contested dimension prunes nothing: two respondents disagreeing means
        nothing is settled, so nothing may be removed on its authority.
        """
        space = self
        for dimension, value in profile.values().items():
            if dimension in space._surviving and isinstance(value, str):
                if value in space._surviving[dimension]:
                    space = space.answer(dimension, value)
        return space

    # -- exploring --------------------------------------------------------

    def explore(self, dimension: str) -> list[Space]:
        """One space per surviving value of this dimension, everything else held.

        Deliberately *not* a cross product. Enumerating combinations across ~20
        dimensions with ~5 values each does not terminate; varying one at a time
        is linear and answers the question that actually matters -- does this
        dimension change the outcome?
        """
        out = []
        for value in sorted(self._surviving[dimension]):
            try:
                out.append(self.answer(dimension, value))
            except Contradiction:  # pragma: no cover - already excluded
                continue
        return out

    # -- internals --------------------------------------------------------

    def _settle(self, surviving: dict[str, set[str]]) -> dict[str, set[str]]:
        """Apply consequences until nothing more follows.

        A collapsed dimension prunes on its own account, which can collapse
        another, so this runs to a fixed point rather than a single pass.
        """
        while True:
            before = {d: frozenset(v) for d, v in surviving.items()}
            for dimension, candidates in list(surviving.items()):
                if len(candidates) != 1:
                    continue
                entry = self._registry.dimensions.get(dimension)
                if not entry:
                    continue
                for target, removed in entry.prunes.get(next(iter(candidates)), {}).items():
                    if target in surviving:
                        surviving[target] = surviving[target] - set(removed)
                        if not surviving[target]:
                            raise Contradiction(
                                f"nothing left for {target!r} after {dimension}="
                                f"{next(iter(candidates))}"
                            )
            if {d: frozenset(v) for d, v in surviving.items()} == before:
                return surviving

    def _blame(self, dimension: str, value: str) -> str:
        """Which earlier answer removed this option."""
        culprits = [
            f"{answered}={chosen}"
            for answered, chosen in self._answered
            if value in self._registry.dimensions[answered].prunes.get(chosen, {}).get(
                dimension, []
            )
        ]
        return ", ".join(culprits) if culprits else "an earlier answer"
