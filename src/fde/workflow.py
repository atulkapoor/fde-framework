"""The shape of what gets built.

A graph of nodes, ordered by the quality-ceiling relation the components already
declare: perception feeds everything downstream, so it cannot come second.

Nodes carry the three properties the moves act on, and each is derived rather
than asserted by hand:

- **mutative** -- it changes something outside the system, so it needs a gate
  and an idempotency key.
- **irreversible** -- undoing it means an apology rather than a rollback, so it
  needs a critic first.
- **sensitive** -- it handles data that may not leave, so it is pinned inside
  the boundary.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from fde.registry import Registry

# Components that act on the world rather than reasoning about it.
MUTATIVE = {"integration"}

# Components whose failures cannot be taken back by re-running them.
IRREVERSIBLE = {"integration"}

# Components that hold or transform client data. Representation is included on
# purpose: an embedding is recoverable to its source, so "we only send vectors"
# is not a defence.
DATA_HANDLING = {"perception", "representation", "retrieval", "memory", "serving"}


@dataclass
class Node:
    id: str
    type: str
    component: str | None = None
    mutative: bool = False
    irreversible: bool = False
    sensitive: bool = False
    idempotency_key: str | None = None
    unfilled: bool = False

    def key(self) -> tuple:
        return (self.id, self.type, self.mutative, self.irreversible,
                self.sensitive, self.idempotency_key, self.unfilled)


@dataclass
class WorkflowGraph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    placement: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    # -- reading ----------------------------------------------------------

    def ordered(self) -> list[Node]:
        seen, out = set(), []
        for source, target in self.edges:
            for node_id in (source, target):
                if node_id not in seen and node_id in self.nodes:
                    seen.add(node_id)
                    out.append(self.nodes[node_id])
        out.extend(n for i, n in self.nodes.items() if i not in seen)
        return out

    def predecessors(self, node_id: str) -> list[Node]:
        return [self.nodes[s] for s, t in self.edges if t == node_id and s in self.nodes]

    def mutative_nodes(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.mutative]

    def irreversible_nodes(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.irreversible]

    def sensitive_nodes(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.sensitive]

    def has_type(self, node_type: str) -> bool:
        return any(n.type == node_type for n in self.nodes.values())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkflowGraph):
            return NotImplemented
        return (
            sorted(n.key() for n in self.nodes.values())
            == sorted(n.key() for n in other.nodes.values())
            and sorted(self.edges) == sorted(other.edges)
            and self.placement == other.placement
        )

    # -- writing ----------------------------------------------------------

    def insert_before(self, target: str, node: Node) -> None:
        """Put a node in front of another, rewiring what fed the target."""
        self.nodes[node.id] = node
        self.edges = [(s, node.id if t == target else t) for s, t in self.edges]
        self.edges.append((node.id, target))
        self.placement.setdefault(node.id, self.placement.get(target, "in_boundary"))

    def copy(self) -> WorkflowGraph:
        return WorkflowGraph(
            nodes={i: Node(**vars(n)) for i, n in self.nodes.items()},
            edges=list(self.edges),
            placement=dict(self.placement),
            notes=list(self.notes),
        )


def build_graph(decisions, registry: Registry) -> WorkflowGraph:
    """Decisions into a graph, ordered by what caps what."""
    graph = WorkflowGraph()
    sensitive = _is_sensitive(decisions)

    for component, decision in decisions.items():
        # Undecided components become nodes too, marked unfilled. A component
        # that disappears between "you need this" and "here is the design" is a
        # hole nobody finds until build time.
        graph.nodes[component] = Node(
            id=component,
            type=_node_type(decision.approach),
            unfilled=decision.approach is None,
            component=component,
            mutative=component in MUTATIVE,
            irreversible=component in IRREVERSIBLE,
            sensitive=sensitive and component in DATA_HANDLING,
        )
        graph.placement[component] = "in_boundary"

    ordered = _by_caps(list(decisions), registry)
    graph.edges = list(zip(ordered, ordered[1:], strict=False))
    return graph


# --- helpers -------------------------------------------------------------


def _node_type(approach: str | None) -> str:
    if approach is None:
        return "Unfilled"
    return {"managed-api": "ExternalCall", "self-hosted": "LocalModel",
            "serverless-gpu": "RentedModel"}.get(approach, "Step")


def _is_sensitive(decisions) -> bool:
    """Sensitivity is a property of the engagement, not of one node: if data
    may not leave, everything that touches it inherits that."""
    return any(
        d.approach == "self-hosted" or "cannot_leave" in (d.rationale or "")
        for d in decisions.values()
    )


def _by_caps(components: list[str], registry: Registry) -> list[str]:
    """Order by the quality-ceiling relation already declared on components."""
    def depth(component: str) -> int:
        entry = registry.components.get(component)
        return -len(entry.caps) if entry else 0

    return sorted(components, key=lambda c: (depth(c), c))


def idempotency_key(node: Node) -> str:
    """Derived from what the action is, so re-running the same action is a
    no-op rather than a second charge."""
    return hashlib.sha256(f"{node.component}:{node.type}".encode()).hexdigest()[:16]
