"""The engagement lifecycle is computed off the record, never declared,
and an open incident pulls production back to pilot."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from fde.cli import app
from fde.drift import close_incident, open_incident, read_journal
from fde.factlog import load_engagement, start_engagement
from fde.lifecycle import assess, outcome_metrics, record, timeline

runner = CliRunner()


def engagement(tmp_path: Path):
    start_engagement(tmp_path, "acme", statement="Decide each claim.")
    return load_engagement(tmp_path / "acme")


def scored_project(tmp_path: Path, holdout_holds: bool = True) -> Path:
    project = tmp_path / "project"
    (project / "evals").mkdir(parents=True)
    (project / "evals" / "manifest.json").write_text("{}")
    (project / "evals" / "golden.jsonl").write_text(
        "".join(json.dumps({"id": str(i), "input": f"case {i}",
                            "output": {"decision": ["a", "b", "c"][i % 3]}}) + "\n"
                for i in range(30)))
    rows = [
        {"property": "holdout", "measured": "81.3% on 3036 cases (majority 1.9%; abstained "
                                            "10.5%, 86.6% on the answered)",
         "holds": holdout_holds, "why": ""},
        {"property": "edge: a valid request", "measured": "200", "holds": True, "why": ""},
    ]
    (project / "scorecard.json").write_text(json.dumps({"rows": rows, "verdict": "x"}))
    return project


def test_the_stage_is_read_off_the_record(tmp_path):
    eng = engagement(tmp_path)
    life = assess(eng, blocked_gates=["baseline"], project=None)
    assert life.current == "discovery"
    assert life.next_stage.name == "validation"
    assert "blocked by baseline" in life.next_stage.missing[0].evidence

    (eng.artifacts_dir / "pairs.jsonl").write_text('{"id": "a", "input": "x", "output": "y"}\n')
    (eng.artifacts_dir / "holdout.jsonl").write_text('{"id": "h", "input": "x", "output": "y"}\n')
    eng.record_data_access("rows returned", "2026-09-20")
    life = assess(eng, blocked_gates=[], project=None)
    assert life.current == "validation"

    project = scored_project(tmp_path)
    life = assess(eng, blocked_gates=[], project=project)
    assert life.current == "pilot"
    assert life.next_stage.name == "production"


def test_transitions_are_recorded_once_per_change(tmp_path):
    eng = engagement(tmp_path)
    life = assess(eng, blocked_gates=["baseline"])
    first = record(eng, life, today="2026-09-01")
    assert first and first["stage"] == "discovery" and first["from"] is None
    assert record(eng, life, today="2026-09-02") is None  # unchanged: nothing appended
    project = scored_project(tmp_path)
    (eng.artifacts_dir / "pairs.jsonl").write_text('{"id": "a", "input": "x", "output": "y"}\n')
    (eng.artifacts_dir / "holdout.jsonl").write_text('{"id": "h", "input": "x", "output": "y"}\n')
    eng.record_data_access("rows", "2026-09-03")
    moved = record(eng, assess(eng, blocked_gates=[], project=project), today="2026-09-10")
    assert moved["from"] == "discovery" and moved["stage"] == "pilot"
    trail = timeline(eng)
    assert [t["stage"] for t in trail] == ["discovery", "pilot"]
    metrics = outcome_metrics(eng, project)
    assert metrics["days_to_pilot"] == 9 and metrics["transitions"] == 2


def test_an_open_incident_pulls_production_back_to_pilot(tmp_path):
    eng = engagement(tmp_path)
    project = scored_project(tmp_path)
    (eng.artifacts_dir / "pairs.jsonl").write_text('{"id": "a", "input": "x", "output": "y"}\n')
    (eng.artifacts_dir / "holdout.jsonl").write_text('{"id": "h", "input": "x", "output": "y"}\n')
    eng.record_data_access("rows", "2026-09-03")
    eng.record_deployed("bank VPC, platform team, 2026-09-20", "2026-09-20")
    assert assess(eng, blocked_gates=[], project=project).current == "production"

    from fde.drift import Drift, Finding, Journal
    drift = Drift(Journal(answered=100), [Finding("abstention", "40%", "10%", True)])
    incident = open_incident(eng, drift, Path("journal.log"), today="2026-09-21")
    life = assess(eng, blocked_gates=[], project=project)
    assert life.current == "pilot" and incident["id"] in life.regressions[0]
    assert close_incident(eng, incident["id"], "holdout re-scored at 80%; pairs redrawn",
                          today="2026-09-22")
    assert assess(eng, blocked_gates=[], project=project).current == "production"


def test_the_stage_command_prints_the_ladder_and_records(tmp_path):
    engagement(tmp_path)
    result = runner.invoke(app, ["stage", str(tmp_path / "acme"), "--today", "2026-09-20"])
    assert result.exit_code == 0, result.output
    assert "acme: discovery" in result.output and "to reach validation" in result.output
    assert "recorded: start -> discovery" in result.output
    again = runner.invoke(app, ["stage", str(tmp_path / "acme")])
    assert "recorded:" not in again.output


def test_outcomes_and_deployment_are_attested_by_command(tmp_path):
    engagement(tmp_path)
    root = str(tmp_path / "acme")
    assert runner.invoke(app, ["deployed", root, "--note", "runs in the client VPC",
                               "--today", "2026-09-20"]).exit_code == 0
    assert runner.invoke(app, ["outcome", root, "--metric", "adoption=0.62",
                               "--metric", "time_to_first_value_days=14",
                               "--note", "support lead's dashboard, week 3"]).exit_code == 0
    rows = [json.loads(line)
            for line in (tmp_path / "acme" / "outcomes.jsonl").read_text().splitlines()]
    assert rows[0]["metric"] == "adoption" and rows[0]["value"] == 0.62
    listed = runner.invoke(app, ["outcomes", root])
    assert "adoption" in listed.output and "0.62" in listed.output


def test_the_journal_is_read_as_the_exam_reads_the_holdout(tmp_path):
    journal = tmp_path / "journal.log"
    lines = []
    for i in range(60):
        lines.append(json.dumps({"level": "info", "event": "answered", "request_id": str(i),
                                 "decision": "a" if i % 2 else "b", "decided_by": "baseline",
                                 "margin": 3.0 + i % 4}))
    for i in range(30):
        lines.append(json.dumps({"level": "info", "event": "answered", "request_id": f"u{i}",
                                 "decision": "unknown", "decided_by": "abstained", "margin": 0.1}))
    lines.append(json.dumps({"level": "error", "request_id": "e1", "error": "KeyError"}))
    lines.append("not json at all")
    journal.write_text("\n".join(lines) + "\n")
    read = read_journal(journal)
    assert read.answered == 90 and read.abstained == 30 and read.errors == 1
    assert read.decisions["a"] == 30 and read.decisions["b"] == 30
    assert len(read.margins) == 90
