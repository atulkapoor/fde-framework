"""Stop conditions: what evidence would stop the engagement, judged
against what the record measured, with STOP as a stage."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement, start_engagement
from fde.lifecycle import assess, record
from fde.stop import StopError, conditions, evaluate, figures, parse
from fde.stop import record as record_conditions

runner = CliRunner()
HOLDOUT = ("77.5% on 3036 cases (majority 1.9%; abstained 10.5%, 86.6% on the answered)")


def scored(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route each message.")
    eng = load_engagement(tmp_path / "acme")
    project = tmp_path / "project"
    (project / "evals").mkdir(parents=True)
    (project / "evals" / "manifest.json").write_text("{}")
    (project / "evals" / "golden.jsonl").write_text("".join(
        json.dumps({"id": str(i), "input": "x", "output": {"intent": "ab"[i % 2]}}) + "\n"
        for i in range(30)))
    (project / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "measured": HOLDOUT, "holds": True},
        {"property": "external exam", "measured": "75.8% on 3079 cases (majority 1.3%)",
         "holds": True},
        {"property": "edge: a valid request", "measured": "200", "holds": True},
    ]}))
    return eng, project


def test_a_condition_is_a_figure_an_operator_and_a_number():
    assert parse("answered_accuracy < 0.88") == ("answered_accuracy", "<", 0.88)
    assert parse(" adoption>=0.4 ") == ("adoption", ">=", 0.4)
    with pytest.raises(StopError):
        parse("accuracy is bad")
    with pytest.raises(StopError):
        parse("answered_accuracy < high")


def test_figures_come_from_the_card_the_field_and_the_outcomes(tmp_path):
    eng, project = scored(tmp_path)
    (tmp_path / "acme" / "outcomes.jsonl").write_text(
        json.dumps({"metric": "adoption", "value": 0.3, "at": "2026-10-01"}) + "\n"
        + json.dumps({"metric": "adoption", "value": 0.62, "at": "2026-11-01"}) + "\n")
    journal = tmp_path / "j.log"
    journal.write_text("".join(
        json.dumps({"event": "answered", "decision": "a", "decided_by": "baseline",
                    "margin": 2.0}) + "\n" for _ in range(40))
        + "".join(json.dumps({"event": "answered", "decision": "unknown",
                              "decided_by": "abstained", "margin": 0.1}) + "\n"
                  for _ in range(10)))
    measured = figures(eng, project, journal)
    assert measured["answered_accuracy"] == 0.866 and measured["abstain_rate"] == 0.105
    assert measured["external_accuracy"] == 0.758 and measured["adoption"] == 0.62
    assert measured["field_abstain_rate"] == 0.2 and measured["field_error_rate"] == 0.0
    assert measured["field_mix_distance"] == 0.5


def test_a_triggered_condition_makes_stop_the_stage(tmp_path):
    eng, project = scored(tmp_path)
    record_conditions(eng, ["answered_accuracy < 0.88", "adoption < 0.4"], by="Priya",
                      at="2026-09-21")
    assert conditions(eng) == ["answered_accuracy < 0.88", "adoption < 0.4"]
    verdicts = evaluate(conditions(eng), figures(eng, project))
    assert [v.triggered for v in verdicts] == [True, None]
    life = assess(eng, blocked_gates=[], project=project)
    assert life.current == "stopped" and "answered_accuracy < 0.88" in life.stopped[0]
    written = record(eng, life, today="2026-09-21")
    assert written["stage"] == "stopped" and written["stopped"]


def test_recording_stop_conditions_keeps_a_waived_gate_waived(tmp_path):
    eng, project = scored(tmp_path)
    root = str(tmp_path / "acme")
    runner.invoke(app, ["waive", root, "outcome_contract", "--reason", "target after the pilot"])
    before = runner.invoke(app, ["status", root]).output
    record_conditions(eng, ["abstain_rate > 0.35"])
    after = runner.invoke(app, ["status", root]).output
    assert ("outcome_contract" in before) == ("outcome_contract" in after)
    assert "outcome_contract" not in after.split("blocked by")[-1].split("\n")[0]


def test_a_condition_the_record_has_not_measured_is_unjudged_not_triggered(tmp_path):
    eng, project = scored(tmp_path)
    record_conditions(eng, ["adoption < 0.4"])
    assert assess(eng, blocked_gates=[], project=project).current != "stopped"


def test_the_command_records_judges_and_exits_one_when_triggered(tmp_path):
    eng, project = scored(tmp_path)
    root = str(tmp_path / "acme")
    ok = runner.invoke(app, ["stop-when", root, "--when", "abstain_rate > 0.35",
                             "--project", str(project), "--by", "Priya"])
    assert ok.exit_code == 0, ok.output
    assert "recorded 1 stop condition" in ok.output and "ok  abstain_rate > 0.35" in ok.output
    again = runner.invoke(app, ["stop-when", root, "--when", "abstain_rate > 0.35",
                                "--project", str(project)])
    assert "already on record" in again.output
    fired = runner.invoke(app, ["stop-when", root, "--when", "answered_accuracy < 0.88",
                                "--project", str(project)])
    assert fired.exit_code == 1 and "STOP  answered_accuracy < 0.88" in fired.output
    assert "measured 0.866" in fired.output
    stage = runner.invoke(app, ["stage", root, "--project", str(project)])
    assert "acme: stopped" in stage.output and "STOPPED by:" in stage.output
    bad = runner.invoke(app, ["stop-when", root, "--when", "nonsense"])
    assert bad.exit_code == 1 and "a stop condition is" in bad.output


def test_the_deployed_build_is_the_one_the_record_reads_by_default(tmp_path, monkeypatch):
    """The banking record read as stopped from its emitted build while the
    implemented copy beside it, the one actually served, passed: `.last-out`
    named the build, nobody had named the deployment. A deployment that
    names its build is what the record reads from then on."""
    eng, emitted = scored(tmp_path)
    served = tmp_path / "project-agent"
    served.mkdir()
    (served / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "holds": True,
         "measured": "73.7% on 3036 cases (majority 1.9%; abstained 18.2%, 90.2% on the answered)"},
    ]}))
    (eng.root / ".last-out").write_text(str(emitted))
    record_conditions(eng, ["answered_accuracy < 0.88"], by="Priya", at="2026-09-21")
    monkeypatch.chdir(tmp_path)
    before = runner.invoke(app, ["stop-when", str(eng.root)])
    assert "STOP" in before.output and "0.866" in before.output
    attested = runner.invoke(app, ["deployed", str(eng.root), "--note", "served on a laptop",
                                   "--project", str(served), "--by", "Priya"])
    assert attested.exit_code == 0 and str(served) in attested.output
    after = runner.invoke(app, ["stop-when", str(eng.root)])
    assert "STOP" not in after.output and "0.902" in after.output, after.output
    assert "project-agent" in (eng.root / "gates.yaml").read_text()
    # Not a project: refused before anything is written.
    refused = runner.invoke(app, ["deployed", str(eng.root), "--note", "x",
                                  "--project", str(tmp_path / "nowhere")])
    assert refused.exit_code == 1 and "not an emitted project" in refused.output
    assert "project-agent" in (eng.root / "gates.yaml").read_text()
