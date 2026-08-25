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

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from fde.architect import Architecture
from fde.deploy import write_deploy
from fde.intake.samples import build_eval_set, infer_contract, infer_metrics, load_pairs
from fde.moves import BoundaryViolation, assert_boundary
from fde.ops import write_ops
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


TEMPLATES = Path(__file__).resolve().parents[2] / "framework" / "templates"


def emit(
    architecture: Architecture,
    out: Path,
    registry: Registry | None = None,
    templates: Path | None = None,
    pairs_path: Path | None = None,
) -> Path:
    out = Path(out)
    _refuse_if_unsound(architecture, out)
    env = Environment(
        loader=FileSystemLoader(str(templates or TEMPLATES)),
        keep_trailing_newline=True,
        autoescape=False,  # noqa: S701 - emitting Python, not markup
    )

    (out / "app" / "components").mkdir(parents=True, exist_ok=True)
    _write_package(architecture, out)
    _write_components(architecture, out, env)
    _write_pipeline(architecture, out)
    if architecture.graph.sensitive_nodes():
        _write_boundary(architecture, out)
    _write_evals(architecture, out, pairs_path)
    write_deploy(architecture, out)
    write_ops(architecture, out, registry)
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


def _write_components(architecture: Architecture, out: Path, env) -> None:
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
        path.write_text(_implementation(component, decision, realization, env))


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


def _implementation(component: str, decision, realization, env) -> str:
    """The reference implementation if one exists, a scaffold otherwise.

    A scaffold is the honest output when the framework knows what to build and
    not yet how: it fixes the contract and says the body is yours. Emitting
    something that looks finished would be worse.
    """
    try:
        template = env.get_template(realization.template)
    except TemplateNotFound:
        return _scaffold(component, decision, realization)

    return template.render(
        component=component,
        approach=decision.approach,
        stack=realization.stack,
        interface=realization.provides,
        rationale=decision.rationale,
        class_name=_class_name(component),
        rejected=decision.rejected,
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


def _write_evals(architecture: Architecture, out: Path, pairs_path: Path | None) -> None:
    """The measurement the project ships with.

    Seeded from the client's own examples, so the evaluation is about their
    problem from the first run rather than a benchmark that resembles it.
    Without pairs there is still a harness and an error taxonomy -- an empty
    golden set is a gap somebody can see, and no harness at all is one nobody
    finds until they ask how it is going.
    """
    evals = out / "evals"
    evals.mkdir(parents=True, exist_ok=True)

    pairs = load_pairs(pairs_path) if pairs_path and pairs_path.exists() else []
    suite = build_eval_set(pairs) if pairs else None
    contract = infer_contract(pairs) if pairs else None
    metrics = infer_metrics(contract) if contract else ["field_exact_match"]

    for name, cases in (
        ("golden", suite.golden if suite else []),
        ("edge_case", suite.edge_case if suite else []),
        ("adversarial", suite.adversarial if suite else []),
    ):
        (evals / f"{name}.jsonl").write_text(
            "".join(json.dumps(c, default=str) + "\n" for c in cases)
        )

    (evals / "taxonomy.py").write_text(_TAXONOMY)
    (evals / "harness.py").write_text(_HARNESS.format(metrics=json.dumps(metrics)))


_TAXONOMY = '''"""Why a case failed, by source rather than by symptom.

Knowing an answer was wrong tells you how often you fail. Knowing the failure
came from ingestion tells you what to build next, and those are different
questions with different answers.
"""

DATA = "data"                 # the source was wrong or missing before we touched it
INPUT = "input"               # parsing lost or mangled it on the way in
PREDICTION = "prediction"     # the model or rule produced the wrong value
OUTPUT = "output"             # right value, wrong shape or place
SYSTEM = "system"             # timeout, crash, resource exhaustion
INTEGRATION = "integration"   # the boundary between two parts of this

SOURCES = [DATA, INPUT, PREDICTION, OUTPUT, SYSTEM, INTEGRATION]


def classify(expected, actual, context=None):
    """Best-effort attribution. Deliberately conservative: an unattributed
    failure is more useful than a confidently mis-attributed one."""
    context = context or {}
    if context.get("exception"):
        return SYSTEM
    if context.get("parse_losses"):
        return INPUT
    if actual in (None, ""):
        return DATA if context.get("source_missing") else PREDICTION
    if type(actual) is not type(expected):
        return OUTPUT
    return PREDICTION
'''


_HARNESS = '''#!/usr/bin/env python3
"""Run the evaluation. Exits non-zero below the threshold, so CI can gate on it.

Three layers, because golden alone measures the happy path. Edge cases come from
the layouts the corpus barely covers; adversarial cases come from the contract
and describe things nobody supplied -- a missing required field, a value of the
wrong type, an instruction hidden in a document.

A run that scores well on golden and badly on adversarial is not a good system.
It is a system nobody has attacked yet.
"""

import argparse
import json
import sys
from collections import Counter
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.taxonomy import classify  # noqa: E402

HERE = Path(__file__).parent
METRICS = {metrics}


def load(name):
    path = HERE / f"{{name}}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run_layer(name, cases, predict):
    if not cases:
        return {{"layer": name, "cases": 0, "score": None, "note": "no cases supplied"}}

    correct, failures = 0, []
    for case in cases:
        expected = case.get("output", case.get("expect"))
        try:
            actual = predict(case.get("input"))
        except Exception as exc:  # noqa: BLE001
            failures.append({{"id": case.get("id"), "source": classify(
                expected, None, {{"exception": exc}})}})
            continue
        if actual == expected:
            correct += 1
        else:
            failures.append({{"id": case.get("id"),
                             "source": classify(expected, actual)}})

    return {{
        "layer": name,
        "cases": len(cases),
        "score": correct / len(cases),
        # The shape of the failures, which is what decides the next move.
        "by_source": dict(Counter(f["source"] for f in failures)),
        "failures": failures[:10],
    }}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="fail below this on the golden layer")
    args = parser.parse_args()

    def predict(_):
        raise NotImplementedError(
            "wire this to app.pipeline.run once the components are implemented"
        )

    report = [run_layer(n, load(n), predict)
              for n in ("golden", "edge_case", "adversarial")]

    print(f"metrics: {{', '.join(METRICS)}}")
    for layer in report:
        score = "--" if layer["score"] is None else f"{{layer['score']:.1%}}"
        print(f"  {{layer['layer']:12}} {{layer['cases']:4}} cases  {{score}}")
        if layer.get("by_source"):
            print(f"               by source: {{layer['by_source']}}")

    golden = next(layer for layer in report if layer["layer"] == "golden")
    if golden["score"] is not None and golden["score"] < args.min_score:
        print(f"below {{args.min_score:.1%}}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


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
