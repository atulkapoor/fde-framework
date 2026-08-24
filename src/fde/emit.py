"""An architecture onto disk.

Two rules shape this.

**Validate everything before writing anything.** A half-written project is worse
than none: it looks finished, and the parts that are missing are the parts
nobody looks at. Every refusal happens before the first file appears.

**Nothing missing is silent.** A component the framework could not decide gets a
module that raises, carrying the reason, rather than being quietly absent. A
hole that imports cleanly is a hole found in production.
"""

from __future__ import annotations

from pathlib import Path

from fde.architect import Architecture
from fde.moves import BoundaryViolation, assert_boundary
from fde.registry import Registry


class BuildRefused(Exception):
    """Something is wrong that writing files would only obscure."""


UNDECIDED_EXCEPTION = """class UndecidedComponent(RuntimeError):
    \"\"\"In scope, but the framework could not decide it.

    Distinct from a scaffold on purpose. A scaffold means the decision was made
    and the body is yours; this means no decision exists, and running is not the
    fix -- answering the question is.
    \"\"\"
"""


def emit(architecture: Architecture, out: Path, registry: Registry | None = None) -> Path:
    out = Path(out)
    _refuse_if_unsound(architecture, out)

    (out / "app" / "components").mkdir(parents=True, exist_ok=True)
    _write_package(architecture, out)
    _write_components(architecture, out)
    _write_pipeline(architecture, out)
    if architecture.graph.sensitive_nodes():
        _write_boundary(architecture, out)
    _write_project_file(out)
    (out / "ARCHITECTURE.md").write_text(render_architecture(architecture))
    return out


# --- refusals ------------------------------------------------------------


def _refuse_if_unsound(architecture: Architecture, out: Path) -> None:
    try:
        assert_boundary(architecture.graph)
    except BoundaryViolation as exc:
        raise BuildRefused(f"boundary: {exc}") from exc

    if out.exists() and any(out.iterdir()):
        raise BuildRefused(f"{out} is not empty; refusing to write over existing work")


# --- code ----------------------------------------------------------------


def _write_package(architecture: Architecture, out: Path) -> None:
    (out / "app" / "__init__.py").write_text(
        f'"""Generated from an engagement profile.\n\n'
        f"Architecture fingerprint: {architecture.fingerprint()}\n"
        f"Topology: {architecture.topology}\n\n"
        f"Regenerating from the same profile produces the same files, so a diff\n"
        f'between two builds means a decision changed.\n"""\n'
    )
    (out / "app" / "components" / "__init__.py").write_text("")


def _write_components(architecture: Architecture, out: Path) -> None:
    for component, decision in sorted(architecture.decisions.items()):
        path = out / "app" / "components" / f"{component}.py"
        realization = architecture.realizations.get(component)

        if not decision.approach:
            path.write_text(_unfilled(component, decision.rationale))
            continue
        if not realization:
            path.write_text(
                _unfilled(component, architecture.unrealizable.get(component, "no realization"))
            )
            continue
        path.write_text(_scaffold(component, decision, realization))


def _unfilled(component: str, reason: str) -> str:
    """A module that refuses to run, saying what was missing.

    Deliberately not a no-op. Something that imports and returns None is a hole
    that reaches production; something that raises is a hole found on the first
    run, with the reason attached.
    """
    return (
        f'"""{component}: nothing could be decided here.\n\n'
        f"{reason}\n\n"
        f"This module exists so the gap is visible. Answer the question that was\n"
        f'missing and regenerate, or implement it by hand and say so.\n"""\n\n'
        f"{UNDECIDED_EXCEPTION}\n"
        f"def run(*args, **kwargs):\n"
        f"    raise UndecidedComponent(\n"
        f"        {component!r} \" was in scope but could not be decided: \"\n"
        f"        {reason!r}\n"
        f"    )\n"
    )


def _scaffold(component: str, decision, realization) -> str:
    """A module with its contract fixed and its behaviour to be written.

    The interface, the placement and the rationale are decided; the body is not.
    Saying so plainly is better than emitting something that looks finished.
    """
    rejected = "\n".join(
        f"    - {r.id}: {r.reason}" for r in decision.rejected[:4]
    ) or "    - nothing else applied"

    return (
        f'"""{component}: {decision.approach}, via {realization.stack}.\n\n'
        f"{decision.rationale}\n\n"
        f"Rejected here:\n{rejected}\n\n"
        f"Satisfies the {realization.provides} interface. The contract below is\n"
        f"decided; the body is not, and is yours to write.\n"
        f'"""\n\n'
        f"from typing import Any\n\n\n"
        f"class {_class_name(component)}:\n"
        f'    """{realization.provides}, as {decision.approach}."""\n\n'
        f"    interface = {realization.provides!r}\n"
        f"    approach = {decision.approach!r}\n"
        f"    stack = {realization.stack!r}\n\n"
        f"    def run(self, payload: Any) -> Any:\n"
        f"        raise NotImplementedError(\n"
        f"            \"{component} is scaffolded as {decision.approach}; \"\n"
        f'            "implement run() against the {realization.provides} contract"\n'
        f"        )\n"
    )


def _write_pipeline(architecture: Architecture, out: Path) -> None:
    ordered = [n for n in architecture.graph.ordered() if n.component]
    imports = "\n".join(
        f"from app.components import {n.component}" for n in ordered
    )
    steps = "\n".join(
        f"    ({n.component!r}, {n.component}.{_class_name(n.component)}()),"
        for n in ordered
        if not n.unfilled
    )
    return (out / "app" / "pipeline.py").write_text(
        f'"""The order things run in.\n\n'
        f"Ordered by what caps what: a step whose quality bounds another comes\n"
        f"first, so when an answer is wrong there is somewhere to look.\n"
        f'"""\n\n'
        f"{imports}\n\n"
        f"STEPS = [\n{steps}\n]\n\n\n"
        f"def run(payload):\n"
        f"    for name, step in STEPS:\n"
        f"        payload = step.run(payload)\n"
        f"    return payload\n"
    )


def _write_boundary(architecture: Architecture, out: Path) -> None:
    placement = "\n".join(
        f"    {node.id!r}: {architecture.graph.placement.get(node.id, 'in_boundary')!r},"
        for node in sorted(architecture.graph.nodes.values(), key=lambda n: n.id)
    )
    (out / "app" / "boundary.py").write_text(
        '"""Where each step is allowed to run.\n\n'
        "Checked at import, not reviewed in a document. Data that may not leave\n"
        "cannot leave by construction, and an embedding is not an exception --\n"
        "it is recoverable to its source, so it inherits the same placement.\n"
        '"""\n\n'
        f"PLACEMENT = {{\n{placement}\n}}\n\n"
        "SENSITIVE = {\n"
        + "".join(f"    {n.id!r},\n" for n in sorted(architecture.graph.sensitive_nodes(),
                                                     key=lambda n: n.id))
        + "}\n\n\n"
        "def check() -> None:\n"
        '    """Fail loudly if anything sensitive has been moved outside."""\n'
        "    outside = [s for s in SENSITIVE if PLACEMENT.get(s) != 'in_boundary']\n"
        "    if outside:\n"
        "        raise RuntimeError(\n"
        "            f'{outside} handle data that may not leave, but are placed outside'\n"
        "        )\n\n\n"
        "check()\n"
    )


def _write_project_file(out: Path) -> None:
    (out / "pyproject.toml").write_text(
        "[project]\n"
        'name = "generated"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.11"\n'
    )


# --- documents -----------------------------------------------------------


def render_architecture(architecture: Architecture) -> str:
    lines = [
        "# Architecture",
        "",
        f"Topology: **{architecture.topology}**  ",
        f"Fingerprint: `{architecture.fingerprint()}`",
        "",
        "## Decisions",
        "",
        "| Component | Approach | Implemented with | Why |",
        "|---|---|---|---|",
    ]
    for component, decision in sorted(architecture.decisions.decided().items()):
        realization = architecture.realizations.get(component)
        lines.append(
            f"| {component} | {decision.approach} | "
            f"{realization.stack if realization else '--'} | {decision.rationale} |"
        )

    lines += ["", "## Rejected alternatives", "",
              "What this design is not, and why. Usually the more useful half.", ""]
    for component, decision in sorted(architecture.decisions.decided().items()):
        if not decision.rejected:
            continue
        lines.append(f"**{component}**")
        lines += [f"- `{r.id}` -- {r.reason}" for r in decision.rejected]
        lines.append("")

    if architecture.decisions.undecided():
        lines += ["## Not decided", "",
                  "In scope, and nothing in the corpus could fill it. Each emits a module "
                  "that raises rather than one that quietly does nothing.", ""]
        lines += [f"- `{c}`" for c in architecture.decisions.undecided()]
        lines.append("")

    if architecture.disagreements:
        lines += ["## Unresolved -- respondents disagree", "",
                  "Not averaged and not settled. The gap between what a sponsor believes "
                  "and what a user experiences is usually the most useful thing discovery "
                  "produced.", ""]
        for d in architecture.disagreements:
            lines.append(f"**{d.dimension}**")
            lines += [
                f"- {f.respondent.name or f.respondent.role} "
                f"({f.respondent.role}): {f.value}"
                for f in d.facts
            ]
            lines.append("")

    lines += ["## Assumptions", "",
              "Nobody answered these, so nothing was decided on them. Each is a question "
              "worth asking before this is built.", ""]
    lines += [f"- {a}" for a in architecture.assumptions] or ["- none"]

    lines += ["", "## Licences", "",
              "Everything this design pulls in, so it can be checked before a legal "
              "team checks it.", ""]
    for stack, licence in sorted(architecture.licences.items()):
        note = "  **copyleft -- obliges publishing changes**" if stack in (
            architecture.copyleft_licences
        ) else ""
        lines.append(f"- `{stack}`: {licence}{note}")

    return "\n".join(lines) + "\n"


def _class_name(component: str) -> str:
    return "".join(part.capitalize() for part in component.replace("-", "_").split("_"))
