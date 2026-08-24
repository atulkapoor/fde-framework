"""The four engagement moves, as graph transformations.

These are the judgement calls that would otherwise live in an experienced FDE's
head, written down so the build can check them. Each is a pure function from
graph to graph, which gives two properties worth having: they compose in any
order without an argument about precedence, and applying one twice cannot
double the gates it inserts.

Three of them add. One removes -- and a set of moves that only ever adds is not
a method, it is a habit.
"""

from __future__ import annotations

from collections.abc import Callable

from fde.workflow import Node, WorkflowGraph, idempotency_key


class BoundaryViolation(Exception):
    """Something that may not leave was placed where it would."""


def autonomy_vs_safety(graph: WorkflowGraph) -> WorkflowGraph:
    """A gate before every step that changes the world, and a key on the step.

    Never a flat refusal of autonomy and never unbounded autonomy: a gate is
    what lets the ramp be earned later on a measured approval rate.

    The idempotency key matters more than the gate. A gate stops the wrong thing
    being done once; a key derived from the action's content means doing it
    twice cannot charge twice. Structural impossibility beats testing for it.
    """
    out = graph.copy()
    for node in list(out.mutative_nodes()):
        node.idempotency_key = node.idempotency_key or idempotency_key(node)
        gate = f"approve-{node.id}"
        if gate not in out.nodes:
            out.insert_before(node.id, Node(id=gate, type="ApprovalGate"))
    return out


def restraint_vs_craft(graph: WorkflowGraph) -> WorkflowGraph:
    """Take out what the problem does not need.

    The only move that removes. A step nothing feeds and nothing consumes is
    something an architecture acquired rather than chose, and it costs a client
    forever.
    """
    out = graph.copy()
    connected = {n for edge in out.edges for n in edge}
    orphans = [
        i for i, n in out.nodes.items()
        if i not in connected and n.type == "Step" and len(out.nodes) > 1
    ]
    for orphan in orphans:
        del out.nodes[orphan]
        out.placement.pop(orphan, None)
    out.notes = [*out.notes, f"restraint: removed {len(orphans)} unconnected step(s)"]
    return out


def data_cannot_leave(graph: WorkflowGraph) -> WorkflowGraph:
    """Split the graph at the boundary and pin what may not cross it.

    Placement is decided here, before anything is generated, rather than
    reviewed afterwards. A boundary discovered during a security review is a
    boundary discovered too late.
    """
    out = graph.copy()
    sensitive = out.sensitive_nodes()
    if not sensitive:
        return out

    if not out.has_type("BoundarySplit"):
        split = Node(id="boundary-split", type="BoundarySplit")
        out.nodes[split.id] = split
        out.placement[split.id] = "in_boundary"
        first = min((n.id for n in sensitive), default=None)
        if first:
            out.edges.append((split.id, first))

    for node in sensitive:
        out.placement[node.id] = "in_boundary"
    return out


def failure_to_leverage(graph: WorkflowGraph) -> WorkflowGraph:
    """A critic before anything that cannot be taken back.

    The point is not to catch every mistake. It is that a mistake caught before
    an irreversible step becomes a regression case, and one caught after becomes
    an apology.
    """
    out = graph.copy()
    for node in list(out.irreversible_nodes()):
        critic = f"critic-{node.id}"
        if critic not in out.nodes:
            out.insert_before(node.id, Node(id=critic, type="Critic"))
    return out


MOVES: dict[str, Callable[[WorkflowGraph], WorkflowGraph]] = {
    "autonomy-vs-safety": autonomy_vs_safety,
    "restraint-vs-craft": restraint_vs_craft,
    "data-cannot-leave": data_cannot_leave,
    "failure-to-leverage": failure_to_leverage,
}


def apply_move(graph: WorkflowGraph, move: str) -> WorkflowGraph:
    if move not in MOVES:
        raise KeyError(f"unknown move {move!r}. Known: {', '.join(sorted(MOVES))}")
    return MOVES[move](graph)


def apply_all(graph: WorkflowGraph) -> WorkflowGraph:
    for move in sorted(MOVES):
        graph = apply_move(graph, move)
    return graph


def assert_boundary(graph: WorkflowGraph) -> None:
    """Fail the build if anything sensitive sits outside.

    An assertion rather than a warning, deliberately. A leak that produces a
    warning is a leak.
    """
    outside = [
        n.id for n in graph.sensitive_nodes() if graph.placement.get(n.id) != "in_boundary"
    ]
    if outside:
        raise BoundaryViolation(
            f"{', '.join(outside)}: handles data that may not leave, but is placed outside "
            f"the boundary"
        )
