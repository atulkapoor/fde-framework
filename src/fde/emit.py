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
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from fde.architect import Architecture
from fde.decide import base_component as _base
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


@dataclass
class EmitReport:
    path: Path
    # Components that fell back to a scaffold because their template was not
    # found. Reported rather than swallowed: a build that silently emits
    # stubs reads as finished, and nothing about it is.
    scaffolded: list[str] = field(default_factory=list)


def emit(
    architecture: Architecture,
    out: Path,
    registry: Registry | None = None,
    templates: Path | None = None,
    pairs_path: Path | None = None,
    waivers: list[dict] | None = None,
    overrides: list[dict] | None = None,
) -> EmitReport:
    out = Path(out)
    _refuse_if_unsound(architecture, out, pairs_path)

    templates = Path(templates) if templates else TEMPLATES
    if not templates.is_dir():
        raise BuildRefused(
            f"{templates}: no templates here. Pass --registry pointing at a "
            f"registry checkout -- building without templates would emit only "
            f"scaffolds and look finished."
        )
    env = Environment(
        loader=FileSystemLoader(str(templates)),
        keep_trailing_newline=True,
        autoescape=False,  # noqa: S701 - emitting Python, not markup
    )

    (out / "app" / "components").mkdir(parents=True, exist_ok=True)
    _write_package(architecture, out)
    scaffolded = _write_components(
        architecture, out, env, sensitive_fields=_sensitive_fields(pairs_path)
    )
    _write_pipeline(architecture, out, registry)
    if architecture.graph.sensitive_nodes():
        _write_boundary(architecture, out)
    _write_evals(architecture, out, pairs_path)
    write_deploy(architecture, out)
    write_ops(architecture, out, registry)
    _write_project_file(out)
    (out / "ARCHITECTURE.md").write_text(render_architecture(architecture, registry))
    _write_risks(out, waivers or [], overrides or [], architecture)
    return EmitReport(path=out, scaffolded=scaffolded)


def _flat(text) -> str:
    """One line, always, and no HTML. Free text renders as text, never as
    structure -- a value carrying its own newlines once forged a `## Gates`
    heading inside the Scope section of a client document."""
    return " ".join(str("" if text is None else text).split()).replace("<", "&lt;")


def _cell(text) -> str:
    """A markdown table cell: flattened, and pipes escaped so a licence
    string cannot shift its row's columns or break out of the table."""
    return _flat(text).replace("|", "\\|")


def _write_risks(out: Path, waivers, overrides, architecture: Architecture) -> None:
    """What was waved through, and what was chosen against the rules.

    Four separate places promise that waivers and conflicting overrides
    "land in the risk section". There was no risk section: a client
    receiving the project could not tell that the baseline gate had been
    waived, let alone that the baseline file was then deleted.
    """
    flat = _flat

    undecided = architecture.decisions.undecided()
    lines = ["# Risks accepted", ""]
    if not waivers and not overrides and not architecture.unrealizable and not undecided:
        lines += [
            "No gate was waived, no recommendation overridden, and every "
            "component in scope has an implementation.",
        ]
    if waivers:
        lines += ["## Gates waived", "",
                  "Each was blocking at build time. Somebody decided to "
                  "proceed anyway, and this is who said what.", ""]
        for waiver in waivers:
            lines.append(
                f"- **{flat(waiver.get('gate'))}** "
                f"({flat(waiver.get('at')) or 'undated'}) -- "
                f"{flat(waiver.get('reason'))}"
            )
            if waiver.get("against"):
                lines.append(f"  - covered: {flat(waiver['against'])}")
        lines.append("")
    if overrides:
        lines += ["## Recommendations overridden", ""]
        for override in overrides:
            lines.append(
                f"- **{flat(override.get('component'))}**: "
                f"{flat(override.get('recommended'))} -> "
                f"{flat(override.get('chosen'))} -- {flat(override.get('because'))}"
            )
            for conflict in override.get("conflicts_with") or []:
                lines.append(f"  - conflicts with `{flat(conflict)}`")
        lines.append("")
    if undecided:
        lines += ["## In scope, undecided", "",
                  "These components are needed and nothing could be chosen "
                  "for them. Their modules raise on use. This is the largest "
                  "risk in the project and it belongs on this page.", ""]
        lines += [
            f"- **{component}** -- {flat(architecture.decisions[component].rationale)}"
            for component in undecided
        ]
        lines.append("")
    if architecture.unrealizable:
        lines += ["## Decided without an implementation", ""]
        lines += [
            f"- **{component}** -- {flat(reason)}"
            for component, reason in sorted(architecture.unrealizable.items())
        ]
        lines.append("")
    (out / "RISKS.md").write_text("\n".join(lines) + "\n")


# --- refusals ------------------------------------------------------------


def _refuse_if_unsound(
    architecture: Architecture, out: Path, pairs_path: Path | None = None
) -> None:
    try:
        assert_boundary(architecture.graph)
    except BoundaryViolation as exc:
        raise BuildRefused(f"boundary: {exc}") from exc

    if out.exists() and any(out.iterdir()):
        raise BuildRefused(f"{out} is not empty; refusing to write over existing work")

    # An architecture in which nothing runs is a no-op wearing a project's
    # clothes: it imports cleanly, returns its input unchanged, and passes an
    # empty evaluation. The usual cause is a profile value the registry does
    # not declare, which decides nothing all the way down.
    if architecture.decisions and not architecture.realizations:
        raise BuildRefused(
            "no component has an implementation -- every step is undecided or "
            "unrealizable. Check the profile's values against the registry's "
            "declared ones; an unrecognised value decides nothing, silently."
        )

    # The pairs file is read last during emission, which is exactly where a
    # malformed line must not first be discovered -- half a project would
    # already be on disk under a success message that scrolled past.
    if pairs_path and Path(pairs_path).exists():
        try:
            infer_contract(load_pairs(pairs_path))
        except Exception as exc:  # noqa: BLE001 - json, contract, os all possible
            raise BuildRefused(f"{pairs_path}: {exc}") from exc


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
    (out / "app" / "contract.py").write_text(
        '"""The one contract every step shares: forbidden input is refused.\n'
        '\n'
        "Raise RefusedInput for input the pipeline must not act on -- a\n"
        "missing field, a type violation, an empty document. The adversarial\n"
        "layer of the eval harness treats RefusedInput as the CORRECT answer\n"
        "to a forbidden probe, and anything else -- a crash, or worse, a\n"
        "confident output -- as the failure it is. Accepting forbidden input\n"
        'is how a system invents an answer nobody can trace.\n"""\n'
        "\n"
        "\n"
        "class RefusedInput(ValueError):\n"
        '    """This input is forbidden by the contract, and saying so is\n'
        '    the correct behaviour."""\n'
    )


def _sensitive_fields(pairs_path: Path | None) -> str:
    """The declared sensitive fields, as a Python tuple body for templates.

    Two sources, unioned: what the contract auto-marked from the field names,
    and what an FDE marked by hand with `fde samples --sensitive`. Declared
    beats detected everywhere else in this framework; here detection only
    ever *adds* caution, so the union is safe.
    """
    if not pairs_path or not Path(pairs_path).exists():
        return ""
    try:
        fields = set(infer_contract(load_pairs(pairs_path)).sensitive_fields)
    except Exception:  # noqa: BLE001 - unreadable pairs already refused earlier
        fields = set()
    marks = Path(pairs_path).parent / "sensitive_fields.json"
    if marks.exists():
        try:
            fields.update(json.loads(marks.read_text()))
        except (json.JSONDecodeError, TypeError):
            pass
    return "".join(f"{name!r}, " for name in sorted(fields))


def _write_components(
    architecture: Architecture, out: Path, env, sensitive_fields: str = ""
) -> list[str]:
    scaffolded = []
    for component, decision in sorted(architecture.decisions.items()):
        path = out / "app" / "components" / f"{_module_name(component)}.py"
        realization = architecture.realizations.get(component)

        if not decision.approach:
            path.write_text(_unfilled(component, decision.rationale))
            continue
        if not realization:
            path.write_text(
                _unfilled(component, architecture.unrealizable.get(component, "no realization"))
            )
            continue
        body, was_scaffold = _implementation(
            component, decision, realization, env, sensitive_fields
        )
        if was_scaffold:
            scaffolded.append(component)
        path.write_text(body)
    return scaffolded


def _module_name(component: str) -> str:
    """An instance key as a Python module name: perception:images ->
    perception_images."""
    return component.replace(":", "_")


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


def _implementation(
    component: str, decision, realization, env, sensitive_fields: str = ""
) -> str:
    """The reference implementation if one exists, a scaffold otherwise.

    A scaffold is the honest output when the framework knows what to build and
    not yet how: it fixes the contract and says the body is yours. Emitting
    something that looks finished would be worse.
    """
    try:
        template = env.get_template(realization.template)
    except TemplateNotFound:
        return _scaffold(component, decision, realization), True

    return template.render(
        component=component,
        approach=decision.approach,
        stack=realization.stack,
        interface=realization.provides,
        rationale=decision.rationale,
        class_name=_class_name(component),
        rejected=decision.rejected,
        sensitive_fields=sensitive_fields,
    ), False


def _guarded(architecture: Architecture, node_id: str) -> str:
    """The component a control node stands in front of.

    Followed transitively: a gate inserted before a step can later find a
    critic inserted between them, and the gate still guards the step, not
    the critic.
    """
    current, hops = node_id, 0
    while hops < len(architecture.graph.nodes):
        node = architecture.graph.nodes.get(current)
        if node is not None and node.component:
            return current
        successor = next(
            (t for s, t in architecture.graph.edges if s == current), None
        )
        if successor is None:
            return current
        current, hops = successor, hops + 1
    return current


def _write_pipeline(architecture: Architecture, out: Path, registry=None) -> None:
    """Every node the moves produced, not only the components.

    An earlier version kept component nodes alone, which silently dropped the
    approval gates and critics the moves had inserted -- the pipeline ran the
    irreversible step with nothing in front of it, and the design document
    described protections the code did not have.
    """
    def _runs(node) -> bool:
        node_entry = architecture.graph.nodes.get(node)
        return node_entry is not None and node_entry.component and not node_entry.unfilled

    def _chains(component: str) -> bool:
        if registry is None:
            return True
        entry = registry.components.get(component)
        return entry.pipeline if entry is not None else True

    ordered = [
        n for n in architecture.graph.ordered()
        if (n.component and _chains(n.component))
        or n.type in ("ApprovalGate", "Critic")
    ]
    # A control guarding a step that is not in the pipeline is worse than
    # absent: a reader sees a governed integration that does not exist.
    controls = [
        n for n in ordered
        if not n.component and _runs(_guarded(architecture, n.id))
    ]
    if controls:
        _write_controls(architecture, out)
    control_ids = {n.id for n in controls}

    running = sorted({
        _module_name(n.id) for n in ordered if n.component and not n.unfilled
    })
    imports = "\n".join(
        f"from app.components import {name}" for name in running
    )
    if controls:
        imports = f"from app import controls\n{imports}"
    if architecture.graph.sensitive_nodes():
        # Importing the pipeline is what starts the system, so this is where
        # the placement check has to live -- a boundary module nothing
        # imports is a boundary reviewed in a document.
        imports = (
            "from app import boundary  # noqa: F401 -- placement checked at import\n"
            + imports
        )

    lines = []
    for n in ordered:
        if n.type == "ApprovalGate" and n.id in control_ids:
            guarded = _guarded(architecture, n.id)
            key = architecture.graph.nodes.get(guarded)
            key_arg = (
                f", idempotency_key={key.idempotency_key!r}"
                if key and key.idempotency_key else ""
            )
            lines.append(
                f"    ({n.id!r}, controls.ApprovalGate(guards={guarded!r}{key_arg})),"
            )
        elif n.type == "Critic" and n.id in control_ids:
            lines.append(
                f"    ({n.id!r}, controls.Critic("
                f"guards={_guarded(architecture, n.id)!r})),"
            )
        elif n.component and not n.unfilled:
            module = _module_name(n.id)
            lines.append(
                f"    ({n.id!r}, {module}.{_class_name(n.id)}()),"
            )
    steps = "\n".join(lines)

    return (out / "app" / "pipeline.py").write_text(
        f'"""The order things run in.\n\n'
        f"Ordered by what caps what: a step whose quality bounds another comes\n"
        f"first, so when an answer is wrong there is somewhere to look.\n"
        f"Approval gates and critics are steps like any other -- removing one\n"
        f"is a visible diff, not an oversight.\n\n"
        f"Only payload-transforming components are chained here. Deployment,\n"
        f"provisioning, evaluation and their kin are decided and emitted, but a\n"
        f"service unit is not a step a payload passes through.\n\n"
        f"The evaluation harness calls run() with each golden case's raw input.\n"
        f"Adapting that input to the first step's payload shape is yours: do it\n"
        f"at the top of run(), where the seam is visible.\n"
        f'"""\n\n'
        f"{imports}\n\n"
        f"STEPS = [\n{steps}\n]\n\n\n"
        f"def run(payload):\n"
        f"    for name, step in STEPS:\n"
        f"        payload = step.run(payload)\n"
        f"    return payload\n"
    )


_CONTROLS = '''"""Fail closed, by construction.

An approval gate that defaults to yes is decoration, and a critic that
defaults to silence is a rubber stamp. Both refuse until wired, so the first
run tells you what has not been decided yet -- instead of quietly doing the
irreversible thing.
"""


class NeedsApproval(RuntimeError):
    """A step that changes the world, with nobody having said yes."""


class CriticRejected(RuntimeError):
    """The check in front of an irreversible step said no."""


class ApprovalGate:
    """Sits in front of a step that changes something outside the system.

    Wire `approve` to a human or a policy. The idempotency key belongs to the
    guarded action: pass it with the side-effect call so that re-running the
    same action is a no-op rather than a second charge.
    """

    def __init__(self, guards, idempotency_key=None, approve=None):
        self.guards = guards
        self.idempotency_key = idempotency_key
        self._approve = approve

    def run(self, payload):
        if self._approve is None:
            raise NeedsApproval(
                f"{self.guards!r} changes the world and nothing approves it yet. "
                f"Construct this gate with approve=<callable> in pipeline.py."
            )
        if not self._approve(payload):
            raise NeedsApproval(f"approval for {self.guards!r} was refused")
        return payload


class Critic:
    """Sits in front of a step whose failure is an apology, not a rollback.

    Wire `review` to return a list of problems; an empty list lets the
    payload through. A mistake caught here becomes a regression case; one
    caught after becomes an apology.
    """

    def __init__(self, guards, review=None):
        self.guards = guards
        self._review = review

    def run(self, payload):
        if self._review is None:
            raise CriticRejected(
                f"{self.guards!r} is irreversible and nothing reviews it yet. "
                f"Construct this critic with review=<callable> in pipeline.py."
            )
        problems = self._review(payload)
        if problems:
            raise CriticRejected(f"{self.guards!r}: {problems}")
        return payload
'''


def _write_controls(architecture: Architecture, out: Path) -> None:
    (out / "app" / "controls.py").write_text(_CONTROLS)


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


_LLM_PROVIDER = '''"""The one place this project talks to a language model.

Configuration is environment, not code:

- LLM_ENDPOINT   an OpenAI-compatible server on this machine or network
                 (vLLM, Ollama) -- the first-class path, because it works
                 inside a boundary.
- LLM_MODEL      model name for that endpoint (or the hosted default).
- ANTHROPIC_API_KEY  the hosted path -- refused outright when this build
                 carries a boundary, because a brief that may not leave
                 does not get to leave via the judge.
"""

from __future__ import annotations

import json
import os
import urllib.request


class ModelUnconfigured(RuntimeError):
    """No model is reachable; nothing here guesses instead."""


def _boundary_present() -> bool:
    try:
        import app.boundary  # noqa: F401
    except ImportError:
        return False
    return True


def complete(prompt: str, timeout: float = 120.0) -> str:
    endpoint = os.environ.get("LLM_ENDPOINT")
    if endpoint:
        body = json.dumps({
            "model": os.environ.get("LLM_MODEL", "default"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode()
        request = urllib.request.Request(
            endpoint.rstrip("/") + "/v1/chat/completions",
            data=body, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)["choices"][0]["message"]["content"]

    if os.environ.get("ANTHROPIC_API_KEY"):
        if _boundary_present():
            raise ModelUnconfigured(
                "this build carries a data boundary, so the hosted model is "
                "refused -- point LLM_ENDPOINT at a model inside it"
            )
        import anthropic

        response = anthropic.Anthropic().messages.create(
            model=os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in response.content if b.type == "text")

    raise ModelUnconfigured(
        "no model is configured -- set LLM_ENDPOINT to an OpenAI-compatible "
        "local server (vLLM or Ollama), or ANTHROPIC_API_KEY where the "
        "boundary allows it"
    )
'''


def _needs_model(architecture: Architecture) -> bool:
    approaches = {
        d.approach for d in architecture.decisions.values() if d.approach
    }
    return bool(approaches & {"judged", "llm", "llm-extraction", "llm-scrubbing",
                              "cascade", "model-planner"})


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

    evaluation = architecture.decisions.get("evaluation")
    judged = bool(evaluation and evaluation.approach == "judged")
    if _needs_model(architecture):
        (out / "app" / "llm.py").write_text(_LLM_PROVIDER)

    (evals / "taxonomy.py").write_text(_TAXONOMY)
    (evals / "harness.py").write_text(
        _HARNESS.format(metrics=json.dumps(metrics), judged=judged)
    )

    golden_count = len(suite.golden) if suite else 0
    (evals / "acceptance.md").write_text(_acceptance(architecture, golden_count))

    latency = (architecture.values or {}).get("latency_budget_ms")
    if latency:
        (evals / "load.py").write_text(
            _LOAD.format(
                latency_ms=int(latency),
                arrival=int((architecture.values or {}).get("arrival_rate") or 0),
            )
        )


def _acceptance(architecture: Architecture, golden_count: int) -> str:
    """The user-acceptance protocol, written down before anyone is asked to
    accept anything.

    The offline harness proves the system agrees with its own golden set.
    Acceptance is a different question -- whether the people who live with the
    output will take it -- and an engagement that never schedules it discovers
    the answer in production.
    """
    judge_note = (
        "the named evaluation owner (the client_readiness gate holds their "
        "name)"
    )
    return "\n".join([
        "# Acceptance",
        "",
        "Offline evaluation says the system matches its examples. This "
        "protocol says whether the people who live with the output accept "
        "it. Run it before production traffic, with the client in the room.",
        "",
        "## Protocol",
        "",
        f"1. **Who judges**: {judge_note}, plus at least one person who does "
        "the work today. Not the builder.",
        f"2. **Sample**: fresh items from live data -- never the golden set "
        f"(the system has seen those {golden_count} in CI). Size to match "
        "the golden set or 30, whichever is larger.",
        "3. **Blind pass**: the judges label the sample before seeing the "
        "system's output; disagreement between judges is recorded, not "
        "resolved by the loudest voice.",
        "4. **Compare**: system output against the blind labels, scored by "
        "the same metrics the harness runs. The baseline's error rate is "
        "the number to beat -- beating zero was never the bar.",
        "5. **Sign-off**: recorded with names and the score. A meeting that "
        "went well is not a sign-off.",
        "",
        "## Refusals worth respecting",
        "",
        "If nobody can be found to judge, that is the client_readiness gate "
        "failing late -- stop and escalate rather than accepting on their "
        "behalf.",
    ]) + "\n"


_LOAD = '''"""Does the built system hold its latency budget under its real arrival rate?

The architecture document quotes p95 under {latency_ms}ms. The offline harness
never verifies that -- it measures correctness one case at a time. This does:
it replays the golden inputs at the engagement\'s stated rate and fails if the
p95 breaches the budget. Like the harness, it fails until the pipeline is
implemented -- a load test that passes against a stub measures the stub.
"""

import json
import statistics
import time
from pathlib import Path

from app.pipeline import run  # noqa: F401 -- raises until implemented, by design

BUDGET_MS = {latency_ms}
ARRIVAL_PER_DAY = {arrival} or 86_400  # unstated -> one per second


def test_p95_under_budget():
    cases = [
        json.loads(line)
        for line in (Path(__file__).parent / "golden.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert cases, "no golden cases -- seed pairs before load-testing"
    laps = []
    for case in cases:
        started = time.perf_counter()
        run(case["input"])
        laps.append((time.perf_counter() - started) * 1000)
    p95 = statistics.quantiles(laps, n=20)[18] if len(laps) >= 20 else max(laps)
    assert p95 <= BUDGET_MS, (
        f"p95 {{p95:.0f}}ms breaches the {{BUDGET_MS}}ms budget the "
        f"architecture quotes"
    )
'''


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


# A freeform answer never equals its reference byte for byte, so a judged
# evaluation scores golden cases with a model comparing candidate to
# reference -- the CI-grade smoke check. Human calibration of the full judge
# stays in evals/acceptance.md; this gate only refuses the obviously wrong.
JUDGED = {judged}
JUDGE_THRESHOLD = 0.7


def judge_score(actual, expected):
    from app.llm import complete

    reply = complete(
        "Reference answer:\\n" + repr(expected) + "\\n\\nCandidate answer:\\n"
        + repr(actual) + "\\n\\nDoes the candidate convey the same content as "
        "the reference? Reply with one number from 0 to 1 and nothing else."
    )
    try:
        return max(0.0, min(1.0, float(reply.strip())))
    except ValueError:
        return 0.0  # an ungradeable reply is a failing grade, visibly


def matches(actual, expected):
    if not JUDGED:
        return actual == expected
    return judge_score(actual, expected) >= JUDGE_THRESHOLD


def run_layer(name, cases, predict):
    if not cases:
        return {{"layer": name, "cases": 0, "score": None, "note": "no cases supplied"}}

    from app.contract import RefusedInput

    correct, errors, failures = 0, 0, []
    for case in cases:
        expected = case.get("output", case.get("expect"))
        if case.get("expect_refusal"):
            # A forbidden probe: refusing IS the correct answer. A crash is
            # an error; a confident output is the failure the probe exists
            # to catch.
            try:
                actual = predict(case.get("input"))
            except RefusedInput:
                correct += 1
            except Exception as exc:  # noqa: BLE001
                errors += 1
                failures.append({{"id": case.get("id"), "source": classify(
                    None, None, {{"exception": exc}})}})
            else:
                failures.append({{"id": case.get("id"),
                                 "source": "prediction",
                                 "note": f"accepted forbidden input: {{actual!r}}"}})
            continue
        try:
            actual = predict(case.get("input"))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            failures.append({{"id": case.get("id"), "source": classify(
                expected, None, {{"exception": exc}})}})
            continue
        if matches(actual, expected):
            correct += 1
        else:
            failures.append({{"id": case.get("id"),
                             "source": classify(expected, actual)}})

    return {{
        "layer": name,
        "cases": len(cases),
        "score": correct / len(cases),
        "errors": errors,
        # The shape of the failures, which is what decides the next move.
        "by_source": dict(Counter(f["source"] for f in failures)),
        "failures": failures[:10],
    }}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="fail below this on the golden layer")
    args = parser.parse_args()

    # The pipeline is the thing under evaluation. While its components are
    # scaffolds -- or a gate is unwired -- every case errors and this run
    # fails, which is the point: a gate that cannot say no is not a gate.
    from app.pipeline import run as predict

    try:
        report = [run_layer(n, load(n), predict)
                  for n in ("golden", "edge_case", "adversarial")]
    except Exception as exc:
        if type(exc).__name__ == "ModelUnconfigured":
            print(f"the evaluation is judge-based and {{exc}}", file=sys.stderr)
            return 1
        raise

    print(f"metrics: {{', '.join(METRICS)}}")
    for layer in report:
        score = "--" if layer["score"] is None else f"{{layer['score']:.1%}}"
        print(f"  {{layer['layer']:12}} {{layer['cases']:4}} cases  {{score}}")
        if layer.get("by_source"):
            print(f"               by source: {{layer['by_source']}}")

    golden = next(layer for layer in report if layer["layer"] == "golden")
    if golden["cases"] == 0:
        # An empty exam graded green once: it printed "not a passing grade"
        # and returned 0, and CI stayed green on a system with no evals.
        print("golden set is empty -- nothing was measured, so nothing "
              "passed. Seed pairs with `fde samples` and rebuild.",
              file=sys.stderr)
        return 1
    if golden.get("errors"):
        print(f"{{golden['errors']}} golden case(s) errored -- the pipeline is "
              f"not yet implemented end to end", file=sys.stderr)
        return 1
    if golden["score"] <= 0:
        print("every golden case failed", file=sys.stderr)
        return 1
    if golden["score"] < args.min_score:
        print(f"below {{args.min_score:.1%}}", file=sys.stderr)
        return 1
    adversarial = next(layer for layer in report if layer["layer"] == "adversarial")
    if adversarial["cases"] and (adversarial.get("errors")
                                 or adversarial["score"] < 1.0):
        print("the attack layer found takers -- an injected instruction was "
              "followed, or forbidden input was accepted or crashed the "
              "pipeline instead of being refused (see failures above)",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _write_project_file(out: Path) -> None:
    # Packages named explicitly: the tree also holds evals/, deploy/ and
    # ops/, and setuptools refuses a flat layout with several top-level
    # directories -- so the emitted CI's `pip install -e .` died at install,
    # before the evaluation it exists to gate ever ran.
    (out / "pyproject.toml").write_text(
        "[project]\n"
        'name = "generated"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.11"\n\n'
        "[build-system]\n"
        'requires = ["setuptools>=68"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        "[tool.setuptools]\n"
        'packages = ["app", "app.components"]\n'
    )


# --- documents -----------------------------------------------------------


SCOPE_LABELS = {
    "functional": "Functional scope",
    "non_functional": "Non-functional scope",
    "data": "Data scope",
    "environment": "Environment",
    "operational": "Operations",
    "commercial": "Commercial",
}


def _scope_sections(architecture: Architecture, registry: Registry | None) -> list[str]:
    """The engagement's scope, stated systematically.

    A solution document that never separates functional from non-functional
    scope reads as a list of trivia; grouped, the same facts read as the
    scoping exercise they were -- and an empty group is a visible hole
    rather than an absence nobody counts.
    """
    if registry is None or not architecture.values:
        return []
    grouped: dict[str, list[tuple[str, object]]] = {}
    for dimension, value in sorted(architecture.values.items()):
        entry = registry.dimensions.get(dimension)
        if entry is None:
            continue
        grouped.setdefault(str(entry.scope), []).append((dimension, value))

    lines = ["## Scope", ""]
    for scope, label in SCOPE_LABELS.items():
        items = grouped.get(scope)
        if not items:
            lines.append(f"**{label}**: not established -- nothing here was "
                         f"stated, measured, or asked to a conclusion.")
            lines.append("")
            continue
        lines.append(f"**{label}**")
        lines.extend(
            f"- `{_flat(d)}` = "
            f"{_flat(', '.join(v) if isinstance(v, tuple) else v)}"
            for d, v in items
        )
        lines.append("")
    return lines


def _tools_section(architecture: Architecture, registry: Registry | None) -> list[str]:
    """Tools and libraries: what was chosen, and what else could serve.

    The corpus holds real stacks; a document that says "plain-python" seven
    times while never mentioning them buries half of what the client is
    paying to know. Alternatives are the ones that actually run in this
    topology -- adopting one is `fde reuse <stack>` and a rebuild, not a
    redesign.
    """
    if registry is None or not architecture.realizations:
        return []
    lines = [
        "## Tools and libraries", "",
        "| Component | Chosen | Licence | Alternatives in this topology |",
        "|---|---|---|---|",
    ]
    from fde.realization import pattern_for

    for component, realization in sorted(architecture.realizations.items()):
        decision = architecture.decisions.get(component)
        try:
            pattern = pattern_for(decision.approach, _base(component), registry)
        except Exception:  # noqa: BLE001 - a missing pattern is not this table's problem
            pattern = None
        alternatives = []
        if pattern is not None:
            alternatives = sorted({
                r.stack for r in pattern.realizations
                if r.stack != realization.stack
                and r.stack in registry.stacks
                and architecture.topology in registry.stacks[r.stack].topologies
            })
        licence = registry.stacks.get(realization.stack)
        lines.append(
            f"| {_cell(component)} | {_cell(realization.stack)} | "
            f"{_cell(licence.licence) if licence else '--'} | "
            f"{_cell(', '.join(alternatives)) if alternatives else '--'} |"
        )
    chosen = {r.stack for r in architecture.realizations.values()}
    idle = sorted(architecture.already_running - chosen)
    if idle:
        lines += [
            "",
            f"Recorded as already running but serving nothing here: "
            f"{', '.join(f'`{_flat(s)}`' for s in idle)} -- no pattern for the "
            f"chosen approaches offers "
            f"{'it' if len(idle) == 1 else 'them'}, so reuse could not take "
            f"effect. That is a corpus statement, not a client one.",
        ]
    lines += [
        "",
        "Adopting an alternative the client already operates: "
        "`fde reuse <engagement> <stack>` and rebuild -- the architecture "
        "does not change, only the emitted code does.",
        "",
    ]
    return lines


def _posture_section(architecture: Architecture) -> list[str]:
    """Agent and tool posture, assembled from what is actually in the graph.

    If the system acts on the world, this says exactly what stands in the
    way of a wrong action -- and if nothing does, that absence is stated
    rather than assumed away.
    """
    graph = architecture.graph
    mutative = [n.id for n in graph.mutative_nodes()]
    if not mutative and not graph.has_type("ApprovalGate"):
        return []
    lines = ["## Agent and tool posture", ""]
    for node_id in sorted(mutative):
        node = graph.nodes[node_id]
        if node.unfilled:
            lines.append(
                f"- `{node_id}` would act on the world but is undecided -- "
                f"no step, gate, or key was emitted. Decide it and rebuild "
                f"before anything here can act."
            )
            continue
        gates = [p.id for p in graph.predecessors(node_id)
                 if p.type in ("ApprovalGate", "Critic")]
        # Walk one hop further: the gate may precede the critic.
        for g in list(gates):
            gates.extend(p.id for p in graph.predecessors(g)
                         if p.type in ("ApprovalGate", "Critic"))
        lines.append(
            f"- `{node_id}` acts on the world. In front of it: "
            f"{', '.join(sorted(set(gates))) or 'nothing -- review this'}; "
            f"idempotency key `{node.idempotency_key or 'unset'}` so re-running "
            f"cannot act twice."
        )
    access = (architecture.values or {}).get("access_model")
    if access == "role_based":
        lines.append(
            "- Access is role-scoped: the approval gate refuses an approval "
            "that names no approver role, and the audit records the role "
            "beside the person. The role names are client content."
        )
    elif access == "open_internal":
        lines.append(
            "- Anyone internal may invoke this, so per-user approval is "
            "impossible by construction -- rate caps and the audit trail "
            "carry what approval cannot."
        )
    elif access == "single_operator":
        lines.append(
            "- One operating team acts here; the audit names people, not "
            "roles."
        )
    integration = architecture.realizations.get("integration")
    if integration is not None:
        lines.append(
            f"- Tool boundary realized via `{integration.stack}`"
            + (" -- the Model Context Protocol, with annotations described "
               "by tools and enforced by the server." if integration.stack == "mcp" else ".")
        )
    reasoning = architecture.decisions.get("reasoning")
    if reasoning is not None and reasoning.approach == "llm":
        # Only the llm template carries max_steps/max_cost. Saying this of an
        # optimiser or a classifier would promise a protection the emitted
        # code does not have.
        lines.append(
            "- The reasoning loop is bounded: a step cap and a budget cap, "
            "and every run records which check ended it."
        )
    lines.append("")
    return lines


def render_architecture(architecture: Architecture, registry: Registry | None = None) -> str:
    lines = [
        "# Architecture",
        "",
        f"Topology: **{architecture.topology}**  ",
        f"Fingerprint: `{architecture.fingerprint()}`",
        "",
        *_scope_sections(architecture, registry),
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

    lines += ["", *_tools_section(architecture, registry)]
    lines += _posture_section(architecture)
    lines += ["", "## Rejected alternatives", "",
              "What this design is not, and why. Usually the more useful half.", ""]
    for component, decision in sorted(architecture.decisions.decided().items()):
        if not decision.rejected:
            continue
        lines.append(f"**{component}**")
        lines += [f"- `{r.id}` -- {r.reason}" for r in decision.rejected]
        lines.append("")

    if architecture.unrealizable:
        lines += [
            "", "## Decided, but not implemented", "",
            "An approach was chosen and no implementation for it exists in "
            "this topology. These modules raise on use rather than pretending "
            "-- the decision stands, the code is yours or the registry's.", "",
        ]
        lines += [
            f"- **{component}** -- {reason}"
            for component, reason in sorted(architecture.unrealizable.items())
        ]
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
    cleaned = component.replace("-", "_").replace(":", "_")
    return "".join(part.capitalize() for part in cleaned.split("_"))
