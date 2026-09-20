"""The production loop: the field read against the exam, an incident
opened on the record when it has moved, closed by name."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from typer.testing import CliRunner

from fde.cli import app
from fde.drift import Journal, detect, expectations, read_journal
from fde.factlog import start_engagement

runner = CliRunner()


def project_with_exam(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "evals").mkdir(parents=True)
    (project / "evals" / "manifest.json").write_text("{}")
    (project / "evals" / "golden.jsonl").write_text(
        "".join(json.dumps({"id": str(i), "input": f"case {i}",
                            "output": {"decision": ["a", "b", "c"][i % 3]}}) + "\n"
                for i in range(90)))
    (project / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "measured": "77.5% on 3036 cases (majority 1.9%; abstained "
                                            "10.5%, 86.6% on the answered)", "holds": True}]}))
    return project


def journal(path: Path, mix: dict[str, int], abstained: int = 0, errors: int = 0) -> Path:
    lines = []
    n = 0
    for label, count in mix.items():
        for _ in range(count):
            lines.append(json.dumps({"event": "answered", "decision": label,
                                     "decided_by": "baseline", "margin": 2.5,
                                     "request_id": str(n)}))
            n += 1
    for _ in range(abstained):
        lines.append(json.dumps({"event": "answered", "decision": "unknown",
                                 "decided_by": "abstained", "margin": 0.2, "request_id": str(n)}))
        n += 1
    for _ in range(errors):
        lines.append(json.dumps({"level": "error", "error": "ValueError", "request_id": str(n)}))
        n += 1
    path.write_text("\n".join(lines) + "\n")
    return path


def test_expectations_come_from_the_exam_and_the_last_card(tmp_path):
    expected = expectations(project_with_exam(tmp_path))
    assert expected["mix"] == Counter({"a": 30, "b": 30, "c": 30})
    assert abs(expected["abstain_rate"] - 0.105) < 1e-9


def test_a_field_that_matches_the_exam_is_quiet(tmp_path):
    project = project_with_exam(tmp_path)
    read = read_journal(journal(tmp_path / "j.log", {"a": 40, "b": 38, "c": 42}, abstained=12))
    drift = detect(read, expectations(project))
    assert not drift.drifted, [f.kind for f in drift.drifted]


def test_abstention_doubling_and_a_shifted_mix_are_drift(tmp_path):
    project = project_with_exam(tmp_path)
    read = read_journal(journal(tmp_path / "j.log", {"a": 100, "b": 5, "c": 5}, abstained=40))
    drift = detect(read, expectations(project))
    kinds = {f.kind for f in drift.drifted}
    assert {"abstention", "decision mix"} <= kinds, kinds


def test_too_few_events_is_a_sample_of_nothing(tmp_path):
    drift = detect(Journal(answered=5, requests=5), {"mix": Counter(), "abstain_rate": 0.1})
    assert not drift.drifted and drift.findings[0].kind == "sample"


def test_the_drift_command_opens_and_closes_an_incident(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route each message.")
    root = tmp_path / "acme"
    project = project_with_exam(tmp_path)
    log = journal(tmp_path / "field.log", {"a": 100, "b": 5, "c": 5}, abstained=40, errors=10)
    result = runner.invoke(app, ["drift", str(root), "--journal", str(log),
                                 "--project", str(project), "--today", "2026-09-21"])
    assert result.exit_code == 1, result.output
    assert "DRIFT" in result.output and "inc-001 opened" in result.output
    rows = [json.loads(line) for line in (root / "incidents.jsonl").read_text().splitlines()]
    assert rows[0]["status"] == "open" and "errors" in rows[0]["kind"]
    listed = runner.invoke(app, ["incident", str(root), "list"])
    assert "inc-001" in listed.output and "open" in listed.output
    closed = runner.invoke(app, ["incident", str(root), "close", "inc-001",
                                 "--note", "holdout re-scored; pairs redrawn"])
    assert closed.exit_code == 0, closed.output
    rows = [json.loads(line) for line in (root / "incidents.jsonl").read_text().splitlines()]
    assert rows[0]["status"] == "closed" and rows[0]["closed_with"]
    quiet = journal(tmp_path / "quiet.log", {"a": 40, "b": 38, "c": 42}, abstained=12)
    ok = runner.invoke(app, ["drift", str(root), "--journal", str(quiet),
                             "--project", str(project)])
    assert ok.exit_code == 0, ok.output
