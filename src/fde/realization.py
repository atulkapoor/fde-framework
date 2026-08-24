"""From a decided approach to the code that implements it.

A pattern says *what*; one realization per stack says *how*. The seam exists
because patterns are stable for years and libraries churn in months, so swapping
a library must change the emitted code and nothing else about the design.

Selection has a fixed order of precedence, and it is not negotiable by
preference:

1. **Topology is a hard filter.** A stack that cannot run where this has to run
   is not a candidate, however good it is.
2. **Reuse beats adoption.** What the client already operates wins, because the
   tenth thing to run is far more expensive than the first.
3. **Otherwise, the simplest.** `plain-python` is a real answer, not a fallback.
"""

from __future__ import annotations

from fde.models.schema import NO_FRAMEWORK, Pattern, Realization
from fde.registry import Registry

# Licences that oblige a client to publish their own changes. Not a judgement --
# many are excellent -- but handing one to a shop that ships proprietary
# software is a problem the framework created, on the engineer's name.
COPYLEFT_MARKERS = ("AGPL", "GPL", "SSPL", "EUPL", "OSL")
PERMISSIVE_WITH_GPL_IN_NAME = ("LGPL",)


class NoRealization(Exception):
    """Nothing in the registry implements this."""


class UnsupportedTopology(Exception):
    """Something implements it, but nothing that can run here."""


def pattern_for(approach: str, component: str, registry: Registry) -> Pattern:
    for pattern in registry.patterns.values():
        if pattern.approach == approach and pattern.component == component:
            return pattern
    raise NoRealization(
        f"no pattern implements approach {approach!r} for component {component!r}"
    )


def realization_for(
    approach: str,
    component: str,
    registry: Registry,
    topology: str,
    already_running: set[str] | None = None,
) -> Realization:
    """Which implementation to emit, given where it has to run."""
    pattern = pattern_for(approach, component, registry)
    running = already_running or set()

    fits = [
        r
        for r in pattern.realizations
        if r.stack in registry.stacks and topology in registry.stacks[r.stack].topologies
    ]
    if not fits:
        raise UnsupportedTopology(
            f"{approach!r} has no realization that runs in {topology!r}; "
            f"offered: {', '.join(sorted(r.stack for r in pattern.realizations))}"
        )

    # Already operated beats newly adopted, and beats plain-python too: a team
    # running Postgres is better served by pgvector than by something hand-rolled.
    reused = [r for r in fits if r.stack in running]
    if reused:
        return reused[0]

    plain = [r for r in fits if r.stack == NO_FRAMEWORK]
    return plain[0] if plain else fits[0]


def licences_for(
    chosen: dict[str, str], registry: Registry, topology: str,
    already_running: set[str] | None = None,
) -> dict[str, str]:
    """Every licence a design drags in, by stack.

    An FDE handing over a project should know this before the client's legal
    team asks, not after.
    """
    found: dict[str, str] = {}
    for component, approach in chosen.items():
        try:
            realization = realization_for(
                approach, component, registry, topology, already_running
            )
        except (NoRealization, UnsupportedTopology):
            continue
        found[realization.stack] = registry.stacks[realization.stack].licence
    return found


def copyleft(licence: str) -> bool:
    """Whether this licence obliges publishing changes.

    Weaker copyleft is treated as permissive here: linking against it does not
    oblige a client to publish their own source, which is the question that
    actually decides whether a design is usable.
    """
    upper = licence.upper()
    if any(marker in upper for marker in PERMISSIVE_WITH_GPL_IN_NAME):
        return False
    return any(marker in upper for marker in COPYLEFT_MARKERS)
