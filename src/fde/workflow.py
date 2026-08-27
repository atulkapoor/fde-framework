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
        """Topological order, deterministically tie-broken by insertion.

        Topological and not edge-list order, and the difference once shipped:
        insert_before appends its rewired edges to the end of the list, so a
        critic inserted in front of an irreversible step *linearised after
        it* -- the emitted pipeline did the unrecoverable thing and then
        reviewed it. The order things run in must be the order the edges
        mean, not the order they were written down.
        """
        indegree = {i: 0 for i in self.nodes}
        for source, target in self.edges:
            if source in self.nodes and target in self.nodes:
                indegree[target] += 1

        ready = [i for i in self.nodes if indegree[i] == 0]
        out: list[Node] = []
        while ready:
            current = ready.pop(0)
            out.append(self.nodes[current])
            for source, target in self.edges:
                if source == current and target in indegree:
                    indegree[target] -= 1
                    if indegree[target] == 0:
                        ready.append(target)

        # A cycle would strand nodes; emit them at the end rather than lose
        # them silently -- a dropped step is worse than an oddly placed one.
        # Compared by node identity, not dict key: a node stored under a key
        # other than its id would otherwise be emitted twice.
        emitted = {id(n) for n in out}
        out.extend(n for n in self.nodes.values() if id(n) not in emitted)
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


def build_graph(decisions, registry: Registry, values: dict | None = None) -> WorkflowGraph:
    """Decisions into a graph, ordered by what caps what."""
    graph = WorkflowGraph()
    sensitive = _is_sensitive(values or {}, registry)

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


def _is_sensitive(values: dict, registry: Registry) -> bool:
    """Sensitivity is a property of the engagement, not of one node: if data
    may not leave, everything that touches it inherits that.

    Read from what the profile says, through what the registry declares.
    An earlier version inferred it from which approach was chosen, which
    missed the exact case the boundary exists for: an air-gapped engagement
    whose serving happened to be decided some other way got no boundary at
    all, silently.
    """
    return any(
        values.get(dimension) in entry.boundary_when
        for dimension, entry in registry.dimensions.items()
        if entry.boundary_when
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
