"""A decision brief from the record: `fde report`.

The framework's reasons lived in two places: the terminal, one command at
a time, and the ARCHITECTURE.md and RISKS.md a build writes. The person
who has to act on the decision -- the sponsor, the department head, the
engineer on the other arm of the experiment -- is often neither at the
terminal nor the owner of a build, and the decision most worth carrying
to them is the one made before a build is authorised, which may be not
to build. This writes that document: one Markdown file, every section
read off the record, nothing estimated.

The readings that are terminal commands are quoted as the terminal
prints them, so the brief cannot say more than the commands do; the
design and the risks are rendered by the same functions a build uses, so
the brief and a later build say the same thing. Sections only appear for
what the record holds; what it lacks is named with the command that
would add it.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

HEADING = re.compile(r"^(#{1,5}) ", re.M)
COMMENT = re.compile(r"<!--.*?-->\s*", re.S)


def capture(argv: list[str]) -> str:
    """One command, in-process, as the terminal would run it. The exit code
    is not part of the brief: a command that refuses explains itself in
    the text, and the text is what is carried."""
    from typer.testing import CliRunner

    from fde.cli import app

    result = CliRunner().invoke(app, argv)
    text = (result.output or "").strip()
    if result.exception and not isinstance(result.exception, SystemExit):
        return f"{text}\n(fde: {type(result.exception).__name__}: {result.exception})".strip()
    return text or "(nothing on record)"


def demote(markdown: str) -> str:
    """A rendered page, dropped one heading level and stripped of its own
    title, so it sits inside the brief's section rather than beside it."""
    lines = markdown.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return HEADING.sub(lambda m: m.group(1) + "# ", "\n".join(lines)).strip()


def without(markdown: str, heading: str) -> str:
    """The page minus one of its sections, where the brief carries the same
    list elsewhere: the architecture's assumptions are the risk page's
    unanswered assumptions, and one document lists them once."""
    lines = markdown.splitlines()
    kept, skipping = [], False
    for line in lines:
        if HEADING.match(line):
            skipping = line.lstrip("#").strip() == heading
        if not skipping:
            kept.append(line)
    return "\n".join(kept).strip()


def figure(value) -> str:
    """A contract figure as a person writes it: `26 h`, not a mapping."""
    if isinstance(value, dict) and "value" in value:
        number = value["value"]
        shown = f"{number:g}" if isinstance(number, (int, float)) else str(number)
        unit = value.get("unit")
        return f"{shown} {unit}" if unit else shown
    return str(value)


def quoted(text: str) -> str:
    return "```text\n" + text.strip() + "\n```"


def statements(root: Path) -> list[str]:
    folder = root / "statements"
    if not folder.is_dir():
        return []
    told = [COMMENT.sub("", p.read_text()).strip() for p in sorted(folder.glob("*.md"))]
    return [t for t in told if t]


def contract(root: Path) -> dict:
    path = root / "outcome.yaml"
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def at_a_glance(engagement, architecture, project: Path | None) -> str:
    """Five stages, five statuses, each read off the record: decided, built,
    implemented, evaluated, outcome. One line each, at the top, so a
    design that was decided is never read as built, a build as
    implemented, a green exam as a measured outcome. An outside reading
    asked for exactly this strip after three worked examples that build,
    and say so, and work nowhere."""
    import json

    from fde.emit import SCAFFOLD_MARK

    if architecture is None:
        decided = "no design yet"
    else:
        undecided = architecture.decisions.undecided()
        decided = f"{len(architecture.decisions.decided())} component(s) decided" + (
            f"; {len(undecided)} undecided: {', '.join(undecided)}" if undecided
            else "; nothing undecided")
    built = f"`{project}`" if project else "not built: nothing on record from `fde build`"
    components = project / "app" / "components" if project else None
    if components and components.is_dir():
        mark = SCAFFOLD_MARK.split("  #")[0]
        scaffolds = sorted(p.stem for p in components.glob("*.py") if mark in p.read_text())
        implemented = (f"{len(scaffolds)} component(s) still scaffolds: {', '.join(scaffolds)}"
                       if scaffolds else "no scaffolds remain")
    else:
        implemented = "not built" if not project else "the build has no app/components to read"
    card = project / "scorecard.json" if project else None
    if card and card.exists():
        try:
            rows = {r["property"]: r for r in json.loads(card.read_text()).get("rows", [])}
        except (ValueError, KeyError, TypeError):
            rows = {}
        holdout = rows.get("holdout")
        verdict = "holds" if holdout and holdout.get("holds") else "does not hold"
        evaluated = (f"holdout {holdout.get('measured')} ({verdict})" if holdout
                     else "a scorecard on record with no holdout row")
    else:
        evaluated = "not scored: `fde scorecard <project> --holdout <file>`"
    outcomes = engagement.root / "outcomes.jsonl"
    recorded = ([line for line in outcomes.read_text().splitlines() if line.strip()]
                if outcomes.exists() else [])
    outcome = (f"{len(recorded)} outcome(s) recorded" if recorded
               else "none recorded: the business impact is not measured")
    return "\n".join([f"- **decided**: {decided}", f"- **built**: {built}",
                      f"- **implemented**: {implemented}", f"- **evaluated**: {evaluated}",
                      f"- **outcome**: {outcome}"])


def what_turns_on(engagement, registry, architecture) -> str:
    """Each unanswered assumption with the decisions that turn on it, so a
    reader can tell an open question that would change the build from one
    that would only narrow the space. The record held this all along --
    `fde next` says it for the next question -- and a reader of the brief
    had it for none of the others."""
    from fde.impact import decision_impact
    from fde.space import Space

    if architecture is None or not architecture.assumptions:
        return "No unanswered assumptions: every dimension the design reads is on the record."
    try:
        space = Space.from_registry(registry).apply(engagement.profile)
    except Exception as exc:  # noqa: BLE001 -- the brief reports, it does not fail
        return f"Not computed: {exc}"
    decisive, narrowing = [], []
    for line in architecture.assumptions:
        dimension = line.split(":", 1)[0].strip()
        try:
            impact = decision_impact(dimension, engagement.profile, registry, space)
        except Exception:  # noqa: BLE001
            narrowing.append(dimension)
            continue
        if not impact.explorable:
            decisive.append(f"- **{dimension}**: decides which approaches exist at all")
        elif impact.differing:
            decisive.append(f"- **{dimension}**: turns on {', '.join(impact.differing)}")
        else:
            narrowing.append(dimension)
    out = decisive or ["- none of the open questions changes a decision yet"]
    if narrowing:
        out.append(f"- narrows the space, not the build ({len(narrowing)}): "
                   + ", ".join(narrowing))
    return "\n".join(out)


def render_report(engagement, registry, registry_root: Path, today: str = "") -> str:
    """The brief, as text. `engagement` is a loaded engagement, `registry`
    a loaded registry; `registry_root` is passed to the commands the brief
    quotes, so they read the same corpus."""
    from fde.architect import architect as build_architecture
    from fde.cli import _overrides, _project_of, _reuse
    from fde.emit import render_architecture, render_risks

    root = engagement.root
    name = root.name
    today = today or date.today().isoformat()
    at = [str(root)]
    reg = ["--registry", str(registry_root)]
    out: list[str] = []

    def section(title: str, lead: str, body: str) -> None:
        out.append(f"## {title}\n\n{lead}\n\n{body}\n")

    out.append(f"# {name}: decision brief\n")
    out.append(f"Written by `fde report` on {today} from the record at `{root}`. Every "
               "figure below is read off that record; nothing here is estimated. Where a "
               "section quotes a command, it is what the command prints today, and running "
               "it again is the way to check.\n")

    told = statements(root)
    if told:
        more = (f"\n\n{len(told) - 1} further statement(s) are on the record; "
                "the facts below draw on all of them." if len(told) > 1 else "")
        section("The problem as stated", "The first statement, as the client put it.",
                "> " + told[0].replace("\n", "\n> ") + more)
    else:
        section("The problem as stated", "No statement is on the record.",
                "`fde start` opens an engagement on one; `fde frame` reads a brief.")

    section("Where the engagement stands",
            "The stage is computed from the evidence on the record, not declared.",
            quoted(capture(["stage", *at, "--no-record", *reg])))

    section("What the record knows, and who said it",
            "Every fact carries its source. A fact learned from a person or inferred is "
            "asserted, not established; the gates below say which ones still need "
            "establishing.",
            quoted(capture(["status", *at, *reg])))

    terms = contract(root)
    fields = [(k, figure(terms.get(k))) for k in ("owner", "metric", "baseline", "target",
                                                   "method", "window")
              if terms.get(k) not in (None, "", {})]
    if fields:
        section("The number this system exists to move",
                "The outcome contract: who owns the figure, where it is today, where it "
                "has to be, measured how, by when.",
                "\n".join(f"- **{k}**: {v}" for k, v in fields))
    else:
        section("The number this system exists to move",
                "No outcome contract is on the record; it is the eighth gate.",
                "`fde outcome-contract` records the owner, the metric, its value today, "
                "the target, the method and the window -- or a waiver saying why not yet.")

    try:
        architecture = build_architecture(
            engagement.profile, registry, overrides=_overrides(engagement),
            already_running=_reuse(engagement))
    except Exception as exc:  # noqa: BLE001 -- the brief reports the refusal, it does not fail
        architecture = None
        section("The design, with its reasons",
                "No design can be built from the record yet.", f"`fde architect` says: {exc}")
    if architecture is not None:
        section("The design, with its reasons",
                "What `fde architect` decides from the facts above, with the approach "
                "each component takes and why; what could not be decided is listed "
                "under the risks. A build writes this same page as ARCHITECTURE.md.",
                without(demote(render_architecture(architecture, registry)), "Assumptions"))
        waivers = engagement.gate_state().get("overrides", []) or []
        section("What the design rests on, and what was accepted",
                "Waived gates, overridden recommendations, assumptions nobody has "
                "answered, and the facts the governance follows from. A build writes "
                "this same page as RISKS.md.",
                demote(render_risks(waivers, [], architecture, registry)))
        section("What each unanswered assumption decides",
                "An open question that would change the build, against one that would "
                "only narrow the space: the first kind is worth a meeting, the second is "
                "not.",
                what_turns_on(engagement, registry, architecture))

    section("Decision debt",
            "Everything the engagement rests on that nobody has settled, each with an "
            "owner and an age.",
            quoted(capture(["debt", *at, *reg, "--as-of", today])))

    section("What would stop this",
            "The conditions on record under which the honest answer is to stop, judged "
            "against what has been measured so far.",
            quoted(capture(["stop-when", *at])))

    if (root / "stakeholders.jsonl").exists():
        section("Who has been heard",
                "Who said what, who signed what, and which roles have not been asked.",
                quoted(capture(["stakeholders", *at])))

    section("The next decision",
            "The single best next action judged from everything above, and what turns "
            "on it.",
            quoted(capture(["next", *at, *reg])))

    # The strip goes under the title, computed last because it reads the
    # design built above.
    out.insert(2, "## At a glance\n\nFive stages, five statuses, none implying the next.\n\n"
                  + at_a_glance(engagement, architecture, _project_of(engagement, None)) + "\n")
    return "\n".join(out).rstrip() + "\n"
