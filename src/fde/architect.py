"""Everything decided, in one object.

`architect` is the join: a profile in, and out comes the component graph, the
decisions, the workflow after the moves have been applied, and the implementation
chosen for each component. It is the thing `emit` writes and the thing a client
reviews, and both need the same information.

Assumptions and disagreements travel with it deliberately. A design that arrives
without them looks more certain than it is, and the questions nobody answered
are exactly what a reader should check.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fde.decide import Decisions, decide_all
from fde.decompose import ComponentGraph, decompose
from fde.graph import TOPOLOGY_DIMENSION
from fde.models.profile import Disagreement, Profile
from fde.moves import apply_all
from fde.realization import (
    NoRealization,
    UnsupportedTopology,
    copyleft,
    realization_for,
)
from fde.registry import Registry
from fde.workflow import WorkflowGraph, build_graph

DEFAULT_TOPOLOGY = "customer-vpc"


@dataclass
class Architecture:
    components: ComponentGraph
    decisions: Decisions
    graph: WorkflowGraph
    topology: str
    realizations: dict[str, object] = field(default_factory=dict)
    licences: dict[str, str] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    disagreements: list[Disagreement] = field(default_factory=list)
    unrealizable: dict[str, str] = field(default_factory=dict)

    # What was known when this was decided. Carried so the documents can quote
    # a stated budget rather than reconstruct it from a rationale.
    values: dict[str, object] = field(default_factory=dict)

    @property
    def copyleft_licences(self) -> dict[str, str]:
        return {s: v for s, v in self.licences.items() if copyleft(v)}

    def fingerprint(self) -> str:
        return self.decisions.decided_fingerprint()


def architect(
    profile: Profile, registry: Registry, already_running: set[str] | None = None
) -> Architecture:
    components = decompose(profile, registry)
    values = profile.values()
    decisions = decide_all(values, registry, components=list(components.components))
    graph = apply_all(build_graph(decisions, registry, values=values))
    topology = values.get(TOPOLOGY_DIMENSION) or DEFAULT_TOPOLOGY

    realizations, licences, unrealizable = {}, {}, {}
    for component, decision in decisions.decided().items():
        try:
            chosen = realization_for(
                decision.approach, component, registry, topology, already_running
            )
        except (NoRealization, UnsupportedTopology) as exc:
            unrealizable[component] = str(exc)
            # The pipeline must not reference a class the module does not
            # define. Unrealizable behaves like undecided: the module exists,
            # says why, and raises on use.
            if component in graph.nodes:
                graph.nodes[component].unfilled = True
            continue
        realizations[component] = chosen
        licences[chosen.stack] = registry.stacks[chosen.stack].licence

    return Architecture(
        components=components,
        decisions=decisions,
        graph=graph,
        topology=topology,
        realizations=realizations,
        licences=licences,
        assumptions=_assumptions(profile, registry),
        disagreements=profile.disagreements(),
        unrealizable=unrealizable,
        values=dict(values),
    )


def _assumptions(profile: Profile, registry: Registry) -> list[str]:
    """Every dimension a decision could have used and nobody answered.

    Stated rather than defaulted. A design that hides what it guessed reads as
    more certain than it is, and the guesses are the first thing worth checking.
    """
    return [
        f"{dimension}: not stated, so nothing was decided on it"
        for dimension in sorted(registry.dimensions)
        if not profile.resolved(dimension)
    ]
