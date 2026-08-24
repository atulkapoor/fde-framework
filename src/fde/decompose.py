"""Profile into a component graph.

A component is included only when a condition it declares actually fires, and it
records which one. Spurious components are how a scope doubles between the
workshop and the statement of work, so "we might need retrieval" is not a
reason to include retrieval -- and not knowing yet is not a reason either.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fde.models.profile import Profile
from fde.models.schema import Component, earliest_cap
from fde.predicate import holds
from fde.registry import Registry


@dataclass
class Included:
    component: Component

    # The conditions that fired. An FDE asked "why is retrieval in scope?"
    # gets a sentence, not a shrug.
    because: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.component.id


@dataclass
class ComponentGraph:
    components: dict[str, Included] = field(default_factory=dict)

    def earliest_cap(self, component_id: str) -> str:
        """Where to look first when this component's quality is capped."""
        return earliest_cap(component_id, {i: v.component for i, v in self.components.items()})

    def __contains__(self, component_id: str) -> bool:
        return component_id in self.components


def decompose(profile: Profile, registry: Registry) -> ComponentGraph:
    graph = ComponentGraph()
    for component in registry.components.values():
        fired = [
            condition
            for condition in component.required_when
            if holds(condition, profile, registry)
        ]
        if fired:
            graph.components[component.id] = Included(component=component, because=fired)
    return graph
