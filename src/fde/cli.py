"""The command line.

`fde kb validate` is strict by default because CI runs it, and a warning nobody
reads is not a check. `--lenient` exists for the hour when you are mid-way
through authoring content and the links do not resolve yet.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
import yaml

from fde.architect import architect as build_architecture
from fde.emit import BuildRefused, emit
from fde.evolution import Override, Prediction, calibration, emit_case, sweep_triggers
from fde.factlog import Session, load_engagement, start_engagement
from fde.gates import HardGate, input_status, validate_baseline
from fde.graph import find_gaps, validate_links
from fde.intake.answers import parse_answer
from fde.intake.documents import UnreadableDocument, read_document
from fde.intake.interview import remaining_questions
from fde.intake.prose import parse_prose, restate
from fde.intake.samples import (
    ContractConflict,
    assess,
    build_eval_set,
    infer_contract,
    infer_metrics,
    load_pairs,
    samples_to_facts,
)
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.models.respondent import Respondent, Role
from fde.registry import KINDS, RegistryError, load_registry
from fde.scan import (
    GPU,
    Hardware,
    detect,
    finetune_feasible,
    fits,
    scan_facts,
    suggest,
)
from fde.space import Contradiction, Space

app = typer.Typer(help="Take an engagement from problem statement to a runnable project.")
kb = typer.Typer(help="Inspect the knowledge base in framework/.")
app.add_typer(kb, name="kb")

DEFAULT_ROOT = Path("framework")


@kb.command("validate")
def kb_validate(
    root: Annotated[Path, typer.Option(help="Registry directory.")] = DEFAULT_ROOT,
    lenient: Annotated[
        bool, typer.Option(help="Report dangling links without failing.")
    ] = False,
) -> None:
    """Check that everything parses and every cross-reference resolves."""
    try:
        registry = load_registry(root)
    except RegistryError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    errors = validate_links(registry)
    for error in errors:
        typer.echo(f"{error.source}: {error.message}", err=not lenient)

    counts = ", ".join(
        f"{len(getattr(registry, kind))} {kind}"
        for kind in KINDS
        if getattr(registry, kind, None)
    )
    typer.echo(f"loaded {counts or 'nothing'}")

    if errors and not lenient:
        typer.echo(f"{len(errors)} broken reference(s)", err=True)
        raise typer.Exit(1)


@app.command("start")
def start(
    name: Annotated[str, typer.Argument(help="Engagement name.")],
    base: Annotated[Path, typer.Option(help="Where engagements live.")] = Path("engagements"),
    statement: Annotated[
        str | None, typer.Option(help="The problem, in prose. Optional.")
    ] = None,
) -> None:
    """Begin an engagement.

    A statement is optional: an FDE who only answers questions is a supported
    path, and so is pasting prose later.
    """
    try:
        engagement = start_engagement(base, name, statement=statement)
    except FileExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"started {engagement.root}")
    typer.echo("  facts/      one file per session, append-only")
    typer.echo("  artifacts/  drop specs, schemas and sample pairs here")
    if not statement:
        typer.echo("\nNo statement yet. Add prose later, or start answering questions.")


@app.command("status")
def status(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
) -> None:
    """What is known, what is contested, and who said it."""
    engagement = load_engagement(root)
    profile = engagement.profile

    # An empty profile is not an empty engagement: a baseline, a waiver or a
    # restated problem are all state the gates judge, facts or no facts.
    if profile.is_empty():
        typer.echo("no facts recorded yet")

    resolved = profile.values()
    if resolved:
        typer.echo(f"known ({len(resolved)})")
        for dimension in sorted(resolved):
            fact = profile.fact(dimension)
            typer.echo(f"  {dimension} = {fact.value}   [{_who(fact)}]")

    status = _gate_status(engagement)
    typer.echo(f"\n{status.completeness:.0%} of what gets decided is settled")

    if status.overridden:
        typer.echo(f"\nwaived ({len(status.overridden)})")
        for waived in status.overridden:
            typer.echo(f"  {waived.gate}: {waived.reason}")

    blocking = status.blocked_by()
    if blocking:
        typer.echo(f"\nblocked by {len(blocking)}")
        for name in blocking:
            gate = status.gate(name)
            mark = "  [hard] " if gate.hard else "  "
            typer.echo(f"{mark}{name}: {gate.reason}")
            if gate.remedy:
                typer.echo(f"      -> {gate.remedy}")

    if status.missing_roles:
        typer.echo(f"\nnobody has spoken for: {', '.join(status.missing_roles)}")

    # Disagreement is the most valuable thing discovery produces. It goes last so
    # it is the final thing on screen, and it is never summarised away.
    disagreements = profile.disagreements()
    if disagreements:
        typer.echo(f"\nunresolved -- respondents disagree ({len(disagreements)})")
        for d in disagreements:
            typer.echo(f"  {d.dimension}")
            for fact in d.facts:
                typer.echo(f"    {_who(fact)} says {fact.value}")


def _who(fact) -> str:
    """Name and role together.

    The role is not decoration: it is what tells an FDE whose answer to weigh
    for which dimension. A sponsor on latency and a user on latency are
    different kinds of claim.
    """
    role = str(fact.respondent.role)
    name = fact.respondent.name
    return f"{name}, {role}" if name else role


@app.command("frame")
def frame(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    text: Annotated[str | None, typer.Option(help="The brief, inline.")] = None,
    file: Annotated[Path | None, typer.Option(help="A file holding the brief.")] = None,
    registry_root: Annotated[Path, typer.Option("--registry")] = DEFAULT_ROOT,
) -> None:
    """Read prose into facts, and play back what was understood."""
    if not text and not file:
        typer.echo("Give me --text or --file.", err=True)
        raise typer.Exit(1)

    try:
        body = read_document(file) if file else (text or "")
    except UnreadableDocument as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    source = file.name if file else "brief"
    registry = load_registry(registry_root)
    engagement = load_engagement(root)

    facts = parse_prose(body, registry, source=source)
    typer.echo(restate(facts, registry))

    # An empty session file is noise in an append-only log.
    if not facts:
        return

    engagement.append(
        Session(
            session_id=_next_session_id(engagement, "frame"),
            respondent=Respondent(role=Role.SYSTEM),
            facts=facts,
        )
    )


@app.command("samples")
def samples_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    file: Annotated[Path, typer.Option(help="A .jsonl of input/output pairs.")],
) -> None:
    """Read sample pairs: the contract, the metric, and the golden set.

    The most valuable thing a client hands over. A brief describes the problem;
    these describe the answer.
    """
    engagement = load_engagement(root)
    try:
        pairs = load_pairs(file)
        contract = infer_contract(pairs)
    except (ContractConflict, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    suite = build_eval_set(pairs)
    typer.echo(f"{len(pairs)} pairs, {len(contract.fields)} fields\n")
    for name, entry in sorted(contract.fields.items()):
        marks = " ".join(
            m for m in ("required" if entry.required else "optional", entry.sensitivity or "")
            if m
        )
        typer.echo(f"  {name:24} {entry.type:8} {marks}")

    typer.echo(f"\nmetric: {', '.join(infer_metrics(contract))}")
    typer.echo(
        f"evals:  {len(suite.golden)} golden, {len(suite.edge_case)} edge, "
        f"{len(suite.adversarial)} adversarial"
    )
    for warning in assess(pairs):
        typer.echo(f"\n{warning}")

    facts = samples_to_facts(pairs)
    engagement.append(
        Session(
            session_id=_next_session_id(engagement, "samples"),
            respondent=Respondent(role=Role.SYSTEM),
            facts=facts,
        )
    )
    # Kept beside the engagement so build can emit the golden set from them.
    (engagement.artifacts_dir / "pairs.jsonl").write_text(file.read_text())


@app.command("ask")
def ask(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    role: Annotated[str, typer.Option(help="Who you are talking to.")],
    name: Annotated[str | None, typer.Option(help="Their name, for the record.")] = None,
    registry_root: Annotated[Path, typer.Option("--registry")] = DEFAULT_ROOT,
) -> None:
    """Interview one person.

    Questions are scoped to what this role can answer and ordered by how much
    the answer changes. Press enter to skip anything -- an intake that cannot
    get past an unknown is an intake that stops.
    """
    registry = load_registry(registry_root)
    engagement = load_engagement(root)
    respondent = Respondent(role=Role(role), name=name)

    space = Space.from_registry(registry).apply(engagement.profile)
    profile = engagement.profile
    gathered: list[Fact] = []

    # Declining to answer means "not from me, not now" -- never "this can never
    # be known". Held beside the space rather than written into it, so a later
    # answer can still settle it by cascade.
    passed_on: set[str] = set()

    while question := _next(space, profile, registry, role, passed_on):
        answer = _put(registry.dimensions[question.resolves], question)
        if answer is None:
            break  # end of input: keep what we have
        if answer.skipped:
            passed_on.add(question.resolves)
            continue

        fact = Fact(
            question.resolves,
            answer.value,
            Provenance.INTERVIEW,
            kind=registry.dimensions[question.resolves].kind,
        )
        try:
            if question.resolves in space.dimensions():
                space = space.answer(question.resolves, answer.value)
        except Contradiction as exc:
            typer.echo(f"  that conflicts: {exc}")
            continue

        gathered.append(fact)
        profile = _with(profile, fact)

    if not gathered:
        typer.echo("Nothing recorded.")
        return

    engagement.append(
        Session(
            session_id=_next_session_id(engagement, role),
            respondent=respondent,
            facts=gathered,
        )
    )
    typer.echo(f"\nRecorded {len(gathered)} answer(s) from {respondent}.")


def _put(dimension, question):
    """Ask until the answer is usable, or the person declines to give one.

    End of input ends the interview rather than aborting it: whatever was
    gathered up to that point is still worth recording.
    """
    while True:
        try:
            reply = typer.prompt(f"\n{question.asks}", default="", show_default=False)
        except (EOFError, typer.Abort):
            return None
        answer = parse_answer(dimension, reply)
        if answer.usable or answer.skipped:
            return answer
        typer.echo(f"  {answer.probe}")


def _next(space, profile, registry, role, passed_on):
    """The next question this person has not already declined."""
    for question in remaining_questions(space, profile, registry, role=role):
        if question.resolves not in passed_on:
            return question
    return None


def _with(profile: Profile, fact: Fact) -> Profile:
    fresh = Profile()
    for dimension in profile.dimensions():
        fresh.ingest(profile.history(dimension))
    fresh.ingest([fact])
    return fresh


def _next_session_id(engagement, label: str) -> str:
    existing = len(list(engagement.facts_dir.glob("*.yaml")))
    return f"{existing + 1:04d}-{label}"


def _gate_status(engagement):
    """The gates, judged against everything the engagement has recorded.

    Waivers stored on disk are re-applied here rather than baked into the
    verdict, so a hand-edited waiver of the hard gate simply does not take:
    the gate stays in blocked_by, visibly, instead of quietly vanishing.
    """
    state = engagement.gate_state()
    status = input_status(
        engagement.profile,
        baseline=engagement.baseline(),
        data_access=bool(state.get("data_access")),
        original_statement=(
            engagement.original_statement().text if engagement.original_statement() else None
        ),
        current_statement=(
            engagement.current_statement().text if engagement.current_statement() else None
        ),
    )
    for waiver in state.get("overrides", []):
        try:
            status.override(waiver["gate"], waiver["reason"])
        except (HardGate, ValueError, StopIteration):
            continue
    return status


def _refuse_if_blocked(engagement, *, warn_only: bool = False) -> None:
    status = _gate_status(engagement)
    blocking = status.blocked_by()
    if not blocking:
        return
    for name in blocking:
        gate = status.gate(name)
        mark = "[hard] " if gate.hard else ""
        typer.echo(f"  {mark}{name}: {gate.reason}", err=True)
        if gate.remedy:
            typer.echo(f"      -> {gate.remedy}", err=True)
    if warn_only:
        typer.echo(
            "\nproceeding anyway -- a design is thinking, not a deliverable. "
            "`fde build` will refuse until these clear.\n", err=True,
        )
        return
    typer.echo(
        "\nrefused: gates above are unsatisfied. Soft gates take "
        "`fde waive <gate> --reason`; data access has no workaround, only "
        "credentials that return real rows.", err=True,
    )
    raise typer.Exit(1)


@app.command("baseline")
def baseline_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    file: Annotated[Path, typer.Option(help="A YAML file of the measured fields.")],
) -> None:
    """Record the measured baseline: seven fields, sampled, with definitions.

    Stored even when incomplete -- a partial baseline is honest state, and the
    gate will say exactly what it still lacks.
    """
    engagement = load_engagement(root)
    try:
        fields = yaml.safe_load(file.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        typer.echo(f"cannot read {file}: {exc}", err=True)
        raise typer.Exit(1) from exc
    if not isinstance(fields, dict):
        typer.echo(f"{file}: expected a mapping of field to value", err=True)
        raise typer.Exit(1)

    engagement.record_baseline(fields)
    result = validate_baseline(fields)
    if result.ok:
        typer.echo("baseline recorded -- re-measurable, sampled, complete")
    else:
        typer.echo(f"recorded, but not yet a baseline: {result.reason}")


@app.command("data-access")
def data_access_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    note: Annotated[str, typer.Option(
        help="What was connected to and what came back. Promised access is not access."
    )],
) -> None:
    """Attest that credentials returned real data.

    The note is the evidence: name the system and what it returned. An
    attestation without one is a promise, and the gate exists because promises
    are what cost three weeks.
    """
    if not note.strip():
        typer.echo("the note is the evidence -- say what returned real rows", err=True)
        raise typer.Exit(1)
    engagement = load_engagement(root)
    engagement.record_data_access(note=note, at=date.today().isoformat())
    typer.echo("data access recorded")


@app.command("waive")
def waive_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    gate: Annotated[str, typer.Argument(help="Which gate to wave through.")],
    reason: Annotated[str, typer.Option(help="Why. Lands in the risk section.")],
) -> None:
    """Override a soft gate, with the reason recorded.

    You are on site and can see things a checklist cannot. The hard gate is the
    exception: nothing can waive absent credentials.
    """
    engagement = load_engagement(root)
    status = _gate_status(engagement)
    try:
        status.override(gate, reason)
    except HardGate as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    except StopIteration:
        names = ", ".join(g.name for g in status.gates)
        typer.echo(f"no gate named {gate!r}. The gates: {names}", err=True)
        raise typer.Exit(1) from None

    engagement.record_waiver(gate=gate, reason=reason, at=date.today().isoformat())
    typer.echo(f"waived {gate} -- recorded for the risk section")


@app.command("restate")
def restate_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    text: Annotated[str | None, typer.Option(help="The problem as now stated.")] = None,
    file: Annotated[Path | None, typer.Option(help="Or a file holding it.")] = None,
    reason: Annotated[str, typer.Option(help="What changed and why.")] = "",
) -> None:
    """Record a new version of the problem statement.

    Version 1 is never edited; drift is measured against it. Restating is how
    the scope-drift gate gets something real to measure.
    """
    if not text and not file:
        typer.echo("give --text or --file", err=True)
        raise typer.Exit(1)
    if not reason.strip():
        typer.echo(
            "a restatement needs --reason: scope that moves without one is "
            "drift by definition", err=True,
        )
        raise typer.Exit(1)

    engagement = load_engagement(root)
    body = text or file.read_text()
    engagement.revise_statement(body.strip(), reason=reason)
    typer.echo(
        f"statement v{len(engagement.statements)} recorded -- drift is still "
        f"measured against v1"
    )


@app.command("architect")
def architect_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    registry_root: Annotated[Path, typer.Option("--registry")] = DEFAULT_ROOT,
) -> None:
    """Decide the design, and say what is still open."""
    registry = load_registry(registry_root)
    engagement = load_engagement(root)
    _refuse_if_blocked(engagement, warn_only=True)
    architecture = build_architecture(engagement.profile, registry)

    typer.echo(f"topology {architecture.topology}   [{architecture.fingerprint()}]\n")
    for component, decision in sorted(architecture.decisions.decided().items()):
        realization = architecture.realizations.get(component)
        via = f" via {realization.stack}" if realization else ""
        typer.echo(f"  {component:16} {decision.approach}{via}")

    if architecture.decisions.undecided():
        typer.echo(f"\nnot decided: {', '.join(architecture.decisions.undecided())}")
    if architecture.disagreements:
        typer.echo(f"\nunresolved: {', '.join(d.dimension for d in architecture.disagreements)}")
    if architecture.copyleft_licences:
        typer.echo(f"\ncopyleft: {', '.join(architecture.copyleft_licences)}")


@app.command("override")
def override_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    component: Annotated[str, typer.Option(help="Which component.")],
    choose: Annotated[str, typer.Option(help="What to use instead.")],
    because: Annotated[str, typer.Option(help="Why. Recorded, never argued with.")],
    registry_root: Annotated[Path, typer.Option("--registry")] = DEFAULT_ROOT,
) -> None:
    """Choose differently from the recommendation.

    Never warns and never blocks. You are on site and know things the rules do
    not -- what is recorded is which rule was overridden, because that is the
    signal, and arguing with you would teach the framework nothing.
    """
    registry = load_registry(registry_root)
    engagement = load_engagement(root)
    architecture = build_architecture(engagement.profile, registry)

    decision = architecture.decisions.get(component)
    recommended = decision.approach if decision else None
    conflicts = [
        c for c in (f"data_residency={engagement.profile.get('data_residency')}",)
        if engagement.profile.get("data_residency") == "cannot_leave"
        and choose in ("managed-api", "managed-embedding")
    ]

    record = Override(
        component=component, recommended=recommended or "nothing", chosen=choose,
        because=because, overrode_rule=recommended or "none", conflicts_with=conflicts,
    )
    engagement.append(
        Session(
            session_id=_next_session_id(engagement, f"override-{component}"),
            respondent=Respondent(role=Role.SYSTEM),
            facts=[Fact(f"override.{component}", choose, Provenance.OBSERVATION,
                        source=because)],
        )
    )
    (engagement.root / "overrides.jsonl").open("a").write(
        json.dumps(record.__dict__) + "\n"
    )

    if recommended:
        typer.echo(f"recorded: {component} {recommended} -> {choose}")
    else:
        # Nothing was recommended, so nothing was overridden. Still worth
        # recording: a component chosen where the framework had no opinion is
        # a gap in the corpus, not a disagreement with it.
        typer.echo(
            f"recorded: {component} -> {choose}\n"
            f"  nothing was recommended here, so this is a gap in the corpus "
            f"rather than a disagreement with it"
        )
    if conflicts:
        # Flagged, not refused. It goes in the risk section rather than in the
        # way.
        typer.echo(f"  conflicts with {', '.join(conflicts)} -- noted in the risks")


@app.command("retro")
def retro_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    outcome: Annotated[str, typer.Option(help="What actually happened.")] = "",
    days: Annotated[int, typer.Option(help="How long it took.")] = 0,
    today: Annotated[str, typer.Option(help="Sweep date, for reproducibility.")] = "",
    registry_root: Annotated[Path, typer.Option("--registry")] = DEFAULT_ROOT,
) -> None:
    """What this engagement taught. Capture only -- no rule is changed here.

    Rules cannot be revised until engagements have outcomes, and pretending to
    revise on a handful would be borrowing rigour rather than having it. What
    this does is make sure nothing is lost in the meantime.
    """
    registry = load_registry(registry_root)
    engagement = load_engagement(root)
    architecture = build_architecture(engagement.profile, registry)

    stamp = today or date.today().isoformat()
    predictions = [
        Prediction(trigger=f"{component}.graduate", condition=decision.rationale,
                   predicted_at=stamp, horizon_days=90)
        for component, decision in architecture.decisions.decided().items()
    ]
    observations = sweep_triggers(predictions, observations=[], today=stamp)
    report = calibration(observations)

    case = emit_case(
        engagement=root.name,
        profile=engagement.profile.values(),
        decisions={c: d.approach for c, d in architecture.decisions.decided().items()},
        observations=observations,
        outcome=outcome or "not stated",
        days=days or None,
        reused=sorted({r.stack for r in architecture.realizations.values()}),
    )
    (engagement.root / "case.json").write_text(json.dumps(case, indent=2, default=str))

    typer.echo(f"case {case['id']}  ({len(case['decisions'])} decisions)")
    typer.echo(f"  triggers: {report['fired']} fired, "
               f"{report['expired_unfired']} expired unfired")
    typer.echo(f"  evidence: {report['strength']} -- {report['why']}")
    typer.echo("\nNothing in framework/ was changed. Revision needs a corpus, "
               "and this is how the corpus gets one.")


@app.command("build")
def build_cmd(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
    out: Annotated[Path, typer.Option(help="Where to write the project.")],
    registry_root: Annotated[Path, typer.Option("--registry")] = DEFAULT_ROOT,
) -> None:
    """Emit the project. Refuses before writing anything if it would be unsound."""
    registry = load_registry(registry_root)
    engagement = load_engagement(root)
    _refuse_if_blocked(engagement)
    architecture = build_architecture(engagement.profile, registry)
    try:
        report = emit(architecture, out, registry=registry,
                      templates=Path(registry_root) / "templates",
                      pairs_path=Path(root) / "artifacts" / "pairs.jsonl")
    except BuildRefused as exc:
        typer.echo(f"refused: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"wrote {out}")
    if architecture.decisions.undecided():
        typer.echo(
            f"  {len(architecture.decisions.undecided())} component(s) raise on use -- "
            f"see ARCHITECTURE.md"
        )
    if architecture.unrealizable:
        typer.echo(
            f"  unrealizable: {', '.join(sorted(architecture.unrealizable))} -- "
            f"raise on use, reasons in ARCHITECTURE.md"
        )
    if report.scaffolded:
        typer.echo(
            f"  scaffolded (template missing): {', '.join(report.scaffolded)} -- "
            f"contracts fixed, bodies to write"
        )


@app.command("scan")
def scan_cmd(
    root: Annotated[Path | None, typer.Argument(help="Engagement to record into.")] = None,
    params_b: Annotated[float, typer.Option("--model-b", help="Model size in billions.")] = 8.0,
    precision: Annotated[str, typer.Option(help="bf16, int8 or int4.")] = "bf16",
    vram: Annotated[float | None, typer.Option(help="Per-card VRAM, if not on the box.")] = None,
    gpus: Annotated[int, typer.Option(help="How many such cards.")] = 1,
) -> None:
    """Whether this hardware runs that model, and what it supports.

    Detects by default. The flags describe a machine you have been told about
    rather than one you are on -- useful for sizing a client's box from your own
    laptop, and never recorded as fact, because a specification somebody quoted
    is not a measurement and the framework decides by provenance.
    """
    measured = vram is None
    hardware = (
        detect() if measured
        else Hardware(gpus=[GPU(f"card-{i}", vram_gb=vram) for i in range(gpus)])
    )

    if hardware.gpus:
        for gpu in hardware.gpus:
            typer.echo(f"  {gpu.model}  {gpu.vram_gb:.0f}GB  sm {gpu.sm}")
    else:
        typer.echo("  no accelerator")
    typer.echo(f"  {hardware.total_vram_gb:.0f}GB total"
               f"{'' if measured else '  (stated, not measured)'}")

    fit = fits(hardware, params_b, precision=precision)
    if not hardware.gpus:
        # Against no accelerator the fit arithmetic answers a question nobody
        # asked. What is wanted here is the size, and where it would have to run.
        typer.echo(
            f"\n{params_b:g}B at {precision}: {fit.weights_gb:.0f}GB of weights, "
            f"nothing to load them onto\n"
            f"  -> quantise and run on the {hardware.ram_gb:.0f}GB of host memory "
            f"if nobody is waiting, or serve it somewhere else"
        )
    else:
        verdict = "fits" if fit.ok else f"does not fit, short {fit.shortfall_gb:.0f}GB"
        typer.echo(
            f"\n{params_b:g}B at {precision}: {verdict}\n"
            f"  {fit.weights_gb:.0f}GB weights + {fit.kv_cache_gb:.0f}GB cache "
            f"against {fit.available_gb:.0f}GB usable"
        )
        if not fit.ok:
            typer.echo("  -> quantise, shrink the model, or add cards")

    typer.echo("\nsupported here")
    for option in suggest(hardware):
        typer.echo(f"  {option.id}\n      {option.reason}\n      costs: {option.cost}")

    if hardware.gpus:
        adapt = finetune_feasible(hardware, params_b, method="full")
        if not adapt.ok:
            typer.echo(f"\nfull finetune: no -- {adapt.reason}")

    if root is None:
        return
    if not measured:
        typer.echo("\nnot recorded: stated figures are not detected facts")
        return

    engagement = load_engagement(root)
    engagement.append(
        Session(
            session_id=_next_session_id(engagement, "scan"),
            respondent=Respondent(role=Role.SYSTEM),
            facts=scan_facts(hardware),
        )
    )
    typer.echo("\nrecorded as detected -- outranks anything stated about this box")


@kb.command("gaps")
def kb_gaps(
    root: Annotated[Path, typer.Option(help="Registry directory.")] = DEFAULT_ROOT,
) -> None:
    """Report what the corpus is missing. Work items, not errors -- always exits 0."""
    try:
        registry = load_registry(root)
    except RegistryError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    gaps = find_gaps(registry, templates=root / "templates")
    for gap in gaps:
        typer.echo(f"{gap.kind}: {gap.detail}")
    typer.echo(f"{len(gaps)} gap(s)")


if __name__ == "__main__":  # pragma: no cover
    app()
