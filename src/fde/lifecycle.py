"""The engagement lifecycle: where an engagement stands, read off its record.

`fde build` was where the framework used to stop, and an engagement does
not: it is discovered, validated, prototyped, piloted on cases nobody
chose, put into production, adopted or not, and looked back on. Each
stage here is a set of criteria the record either shows or does not --
a statement, gates, an exam, a build, a scorecard with the out-of-sample
rows holding, a deployment on record with no open incident, an adoption
figure, a retrospective. Nothing is declared; the stage is computed, and
every transition is appended to `lifecycle.jsonl` with the evidence, so
time-to-first-value and every reversal can be read back later.

A stage can go backwards. An open drift incident sends production back to
pilot until the holdout has been scored again and the incident closed:
the system in the field is not the system that was signed off.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

STAGES = ("discovery", "validation", "prototype", "pilot", "production", "adoption",
          "retrospective")


@dataclass
class Criterion:
    name: str
    holds: bool
    evidence: str


@dataclass
class Stage:
    name: str
    criteria: list[Criterion] = field(default_factory=list)

    @property
    def holds(self) -> bool:
        return all(c.holds for c in self.criteria)

    @property
    def missing(self) -> list[Criterion]:
        return [c for c in self.criteria if not c.holds]


@dataclass
class Lifecycle:
    stages: list[Stage]
    regressions: list[str] = field(default_factory=list)

    @property
    def current(self) -> str:
        reached = "none"
        for stage in self.stages:
            if not stage.holds:
                break
            reached = stage.name
        # An open incident pulls production back to pilot.
        if reached in ("production", "adoption") and self.regressions:
            return "pilot"
        return reached

    @property
    def next_stage(self) -> Stage | None:
        for stage in self.stages:
            if not stage.holds:
                return stage
        return None


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def _scorecard(project: Path | None) -> dict[str, dict] | None:
    if project is None or not (project / "scorecard.json").exists():
        return None
    try:
        record = json.loads((project / "scorecard.json").read_text())
        return {r["property"]: r for r in record.get("rows", [])}
    except (ValueError, KeyError, TypeError):
        return None


def open_incidents(root: Path) -> list[dict]:
    return [i for i in _jsonl(root / "incidents.jsonl") if i.get("status") == "open"]


def assess(engagement, blocked_gates: list[str] | None, project: Path | None = None) -> Lifecycle:
    """Every stage's criteria against the record. `blocked_gates` is what
    the gate logic says is still blocking (None when it could not be
    judged); `project` is the emitted project, when one is known."""
    root = Path(engagement.root)
    statement = engagement.current_statement()
    artifacts = root / "artifacts"
    pairs = artifacts / "pairs.jsonl"
    holdout = artifacts / "holdout.jsonl"
    state = engagement.gate_state()
    raw = engagement._raw_gate_state() if hasattr(engagement, "_raw_gate_state") else {}
    deployed = raw.get("deployed") if isinstance(raw, dict) else None
    incidents = open_incidents(root)
    outcomes = _jsonl(root / "outcomes.jsonl")
    card = _scorecard(project)

    discovery = Stage("discovery", [
        Criterion("a problem statement", statement is not None,
                  (statement.text[:80] + "...") if statement and len(statement.text) > 80
                  else (statement.text if statement else "none recorded: fde start")),
    ])
    gates_known = blocked_gates is not None
    validation = Stage("validation", [
        Criterion("the gates pass or are waived on the record",
                  gates_known and not blocked_gates,
                  ("all pass" if gates_known and not blocked_gates
                   else f"blocked by {', '.join(blocked_gates)}" if blocked_gates
                   else "not judged")),
        Criterion("the exam is seeded from the client's pairs", pairs.exists(),
                  f"{sum(1 for line in pairs.read_text().splitlines() if line.strip())} pairs"
                  if pairs.exists() else "none: fde samples"),
        Criterion("a holdout the delivery never ships", holdout.exists(),
                  f"{sum(1 for line in holdout.read_text().splitlines() if line.strip())} cases"
                  if holdout.exists() else "none drawn"),
        Criterion("data access attested", bool(state.get("data_access")),
                  state.get("data_access", {}).get("note", "")[:80]
                  if state.get("data_access") else "none: fde data-access"),
    ])
    built = project is not None and (project / "evals" / "manifest.json").exists()
    prototype = Stage("prototype", [
        Criterion("a build with its exam record", built,
                  str(project) if built else "none: fde build"),
    ])
    holdout_row = card.get("holdout") if card else None
    holdout_holds = bool(holdout_row and holdout_row.get("holds"))
    pilot = Stage("pilot", [
        Criterion("a scorecard on record", card is not None,
                  "scorecard.json" if card else "none: fde scorecard"),
        Criterion("the out-of-sample rows hold", holdout_holds,
                  holdout_row.get("measured", "") if holdout_row
                  else "no holdout row: pass --holdout to fde scorecard"),
        Criterion("the edge answers a valid request",
                  bool(card and card.get("edge: a valid request", {}).get("holds")),
                  card.get("edge: a valid request", {}).get("measured", "not probed")
                  if card else "not probed"),
    ])
    attested = isinstance(deployed, dict) and bool(deployed.get("note"))
    production = Stage("production", [
        Criterion("a deployment on record", attested,
                  deployed.get("note", "")[:80] if attested
                  else "none: fde deployed <eng> --note"),
        Criterion("no open incident", not incidents,
                  "none open" if not incidents
                  else f"{len(incidents)} open: " + ", ".join(i.get("id", "?") for i in incidents)),
    ])
    adoption_rows = [o for o in outcomes if o.get("metric") == "adoption"]
    adoption = Stage("adoption", [
        Criterion("an adoption figure measured in the field", bool(adoption_rows),
                  f"adoption {adoption_rows[-1].get('value')} ({adoption_rows[-1].get('at')})"
                  if adoption_rows else "none: fde outcome <eng> --metric adoption=<share>"),
    ])
    retrospective = Stage("retrospective", [
        Criterion("a retrospective captured as a case", (root / "case.json").exists(),
                  "case.json" if (root / "case.json").exists() else "none: fde retro"),
    ])
    regressions = [f"open incident {i.get('id')}: {i.get('kind')}" for i in incidents]
    return Lifecycle([discovery, validation, prototype, pilot, production, adoption,
                      retrospective], regressions=regressions)


def record(engagement, lifecycle: Lifecycle, today: str | None = None) -> dict | None:
    """Append a transition when the computed stage differs from the last
    recorded one. Returns the transition written, or None."""
    path = Path(engagement.root) / "lifecycle.jsonl"
    history = _jsonl(path)
    last = history[-1]["stage"] if history else None
    current = lifecycle.current
    if last == current:
        return None
    entry = {
        "at": today or date.today().isoformat(),
        "from": last,
        "stage": current,
        "evidence": {
            stage.name: [c.evidence for c in stage.criteria]
            for stage in lifecycle.stages if stage.name == current
        },
        "regressions": lifecycle.regressions,
    }
    with path.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")
    return entry


def timeline(engagement) -> list[dict]:
    return _jsonl(Path(engagement.root) / "lifecycle.jsonl")


def render(lifecycle: Lifecycle, name: str) -> str:
    lines = [f"{name}: {lifecycle.current}", ""]
    for stage in lifecycle.stages:
        mark = "ok " if stage.holds else "-- "
        lines.append(f"  {mark}{stage.name}")
        for criterion in stage.criteria:
            tick = "ok " if criterion.holds else "NO "
            lines.append(f"       {tick}{criterion.name}: {criterion.evidence}")
    if lifecycle.regressions:
        lines += ["", "regressed to pilot by: " + "; ".join(lifecycle.regressions)]
    nxt = lifecycle.next_stage
    if nxt:
        first = nxt.missing[0] if nxt.missing else None
        if first:
            lines += ["", f"to reach {nxt.name}: {first.name} -- {first.evidence}"]
    return "\n".join(lines)


def outcome_metrics(engagement, project: Path | None = None) -> dict[str, Any]:
    """What can be read off the record without anyone's opinion: days
    from the first recorded stage to pilot, rounds the loop took,
    architecture reversals (overrides), incidents opened and closed,
    outcomes, and the transitions themselves."""
    root = Path(engagement.root)
    trail = timeline(engagement)
    first_pilot = next((t["at"] for t in trail if t["stage"] in ("pilot", "production")), None)
    first_stage = trail[0]["at"] if trail else None
    days_to_pilot = None
    if first_stage and first_pilot:
        days_to_pilot = (date.fromisoformat(first_pilot) - date.fromisoformat(first_stage)).days
    overrides = _jsonl(root / "overrides.jsonl")
    incidents = _jsonl(root / "incidents.jsonl")
    outcomes = _jsonl(root / "outcomes.jsonl")
    rounds = 0
    log = (project / "ops" / "implement-log.md") if project else None
    if log and log.exists():
        rounds = log.read_text().count("\n## Round ")
    return {
        "stage": trail[-1]["stage"] if trail else None,
        "transitions": len(trail),
        "days_to_pilot": days_to_pilot,
        "implement_rounds_logged": rounds,
        "architecture_reversals": len(overrides),
        "incidents_opened": len(incidents),
        "incidents_open": sum(1 for i in incidents if i.get("status") == "open"),
        "outcomes_recorded": {o.get("metric"): o.get("value") for o in outcomes},
        "first_recorded": first_stage,
    }
