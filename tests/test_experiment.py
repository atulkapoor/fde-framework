"""The experiment run by the record: arms assigned by a balanced seeded
draw, what was known frozen before the build, measures read off the
record or the control log, a packet with no arm in it, a review with a
guess, a report that says what its count can show."""

from __future__ import annotations

import json

import pytest
import yaml
from typer.testing import CliRunner

from fde import experiment as exp
from fde.cli import app
from fde.factlog import Session, load_engagement, start_engagement
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.respondent import Respondent, Role

runner = CliRunner()
HOLDOUT = "77.5% on 3036 cases (majority 1.9%; abstained 10.5%, 86.6% on the answered)"


def engagement(tmp_path, name, shape="decision"):
    start_engagement(tmp_path / "engagements", name, statement=f"Decide {name}.")
    eng = load_engagement(tmp_path / "engagements" / name)
    eng.append(Session(session_id="0001-sponsor",
                       respondent=Respondent(role=Role.SPONSOR, name="Priya"),
                       facts=[Fact("output_shape", shape, Provenance.INTERVIEW),
                              Fact("external_systems", 2, Provenance.INTERVIEW)]))
    return eng


def scored_project(tmp_path):
    project = tmp_path / "project"
    (project / "evals").mkdir(parents=True)
    (project / "evals" / "manifest.json").write_text("{}")
    (project / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "measured": HOLDOUT, "holds": True}]}))
    return project


def test_arms_are_balanced_within_the_shape_and_the_draw_is_seeded():
    series = {"seed": 7, "engagements": []}
    first, how = exp.assign(series, "decision", 1)
    assert first in exp.ARMS and how.startswith("seeded draw")
    assert exp.assign(series, "decision", 1) == (first, how)  # reproducible
    series["engagements"].append({"shape": "decision", "arm": first})
    second, how = exp.assign(series, "decision", 2)
    assert second != first and how == "balancing the shape"
    assert exp.assign(series, "decision", 3, forced="with") == ("with", "by hand")
    with pytest.raises(ValueError):
        exp.assign(series, "decision", 3, forced="maybe")


def test_start_freezes_what_was_known_and_records_the_difficulty(tmp_path):
    eng = engagement(tmp_path, "acme")
    eng.record_outcome_contract({"owner": "o", "metric": "m", "baseline": {"value": 1},
                                 "target": {"value": 2}, "method": "x", "window": "y"})
    from fde.forecast import record as forecast
    forecast(eng, ["holdout_accuracy >= 0.8"])
    entry = exp.start(eng, "Dev", at="2026-10-01")
    assert entry["shape"] == "decision" and entry["order"] == 1
    assert entry["frozen"]["forecasts"] == ["holdout_accuracy >= 0.8"]
    assert entry["frozen"]["outcome_contract"]["metric"] == "m"
    assert entry["difficulty"]["external_systems"] == 2
    assert entry["difficulty"]["roles_heard"] == ["sponsor"] and entry["difficulty"]["facts"] == 2
    assert entry["difficulty"]["baseline"] == "none" and not entry["built_already"]
    series = json.loads((tmp_path / "engagements" / "experiment-series.json").read_text())
    assert series["engagements"][0]["engagement"] == "acme"
    with pytest.raises(FileExistsError):
        exp.start(eng, "Dev")


def test_the_control_arm_gets_a_log_template_the_same_code_reads(tmp_path):
    eng = engagement(tmp_path, "ctrl")
    entry = exp.start(eng, "Dev", arm="without", at="2026-10-01")
    log_path = tmp_path / "engagements" / "ctrl" / exp.CONTROL_LOG
    assert entry["arm"] == "without" and log_path.exists()
    log = yaml.safe_load(log_path.read_text())
    log["dates"] = {"scoped": "2026-10-01", "pilot": "2026-10-15"}
    log["hours"] = 40
    log["rounds"] = 3
    log["reversals"] = 1
    log["fitness"]["holdout_accuracy"] = 0.7
    log["fitness"]["coverage"] = 0.95
    log["forecast_errors"] = [-0.05, 0.02]
    log["statement"] = "Decide ctrl."
    log["evidence"] = [{"what": "volume 100/day", "basis": "measured"}]
    log["decision"] = {"chosen": "rules", "rejected": [{"approach": "llm", "why": "no need"}]}
    log_path.write_text(yaml.safe_dump(log))
    closing = exp.close(eng, at="2026-10-16")
    m = closing["measures"]
    assert m["days_to_pilot"] == 14 and m["hours"] == 40 and m["forecast_mean_error"] == -0.015
    assert "external_accuracy" in closing["missing"] and "hours" not in closing["missing"]
    text = exp.packet(eng)
    assert "Decide ctrl." in text and "rules" in text and "no need" in text
    assert "without" not in text and "with " not in text.lower().replace("with a", "")


def test_close_reads_the_with_arm_off_the_record_and_lists_what_is_missing(tmp_path):
    eng = engagement(tmp_path, "acme")
    project = scored_project(tmp_path)
    exp.start(eng, "Dev", project=project, arm="with", at="2026-10-01")
    entry = json.loads((tmp_path / "engagements" / "acme" / "experiment.json").read_text())
    assert entry["built_already"] is True
    closing = exp.close(eng, project, at="2026-10-20")
    m = closing["measures"]
    assert m["holdout_accuracy"] == 0.775 and m["coverage"] == 0.895
    assert m["questions_asked"] == 2 and m["hours"] is None
    assert "hours" in closing["missing"] and "external_accuracy" in closing["missing"]


def test_the_review_is_a_fixed_form_with_a_guess(tmp_path):
    eng = engagement(tmp_path, "acme")
    exp.start(eng, "Dev")
    scores = {n: 4 for n in exp.REVIEW_FORM}
    form = exp.review(eng, "Sam", scores, True, "what does the queue cost?", "uncertain")
    assert form["quality"] == 4.0 and form["arm_guess"] == "uncertain"
    with pytest.raises(ValueError):
        exp.review(eng, "Sam", {**scores, "risk": 9}, True, "", "with")
    with pytest.raises(ValueError):
        exp.review(eng, "Sam", scores, True, "", "maybe")
    with pytest.raises(ValueError):
        exp.review(eng, "  ", scores, True, "", "with")


def test_the_report_pairs_arms_and_reports_blinding_and_maturity(tmp_path):
    a = engagement(tmp_path, "a")
    b = engagement(tmp_path, "b")
    project = scored_project(tmp_path)
    exp.start(a, "Dev", project=project, arm="with", at="2026-10-01")
    exp.start(b, "Dev", arm="without", at="2026-10-02")
    exp.close(a, project, at="2026-10-20")
    log_path = tmp_path / "engagements" / "b" / exp.CONTROL_LOG
    log = yaml.safe_load(log_path.read_text())
    log["fitness"]["holdout_accuracy"] = 0.7
    log["reversals"] = 2
    log_path.write_text(yaml.safe_dump(log))
    exp.close(b, at="2026-10-21")
    exp.review(a, "Sam", {n: 4 for n in exp.REVIEW_FORM}, True, "", "with")
    exp.review(b, "Sam", {n: 3 for n in exp.REVIEW_FORM}, False, "", "with")
    text = exp.report(tmp_path / "engagements")
    assert "2 engagement(s)" in text and "descriptive only" in text
    assert "pair a / b: quality +1.00" in text
    import re
    assert re.search(r"holdout_accuracy\s+\+0\.075", text)
    assert "blinding: 1 of 2 decided guesses were right (0 uncertain)" in text
    assert "started after a build existed: a" in text
    assert exp.maturity(5).startswith("paired") and exp.maturity(20).startswith("stronger")


def test_the_command_runs_the_protocol_end_to_end(tmp_path):
    engagement(tmp_path, "acme")
    root = str(tmp_path / "engagements" / "acme")
    started = runner.invoke(app, ["experiment", root, "start", "--engineer", "Dev",
                                  "--arm", "with", "--today", "2026-10-01"])
    assert started.exit_code == 0, started.output
    assert "arm with (by hand)" in started.output and "frozen:" in started.output
    project = scored_project(tmp_path)
    closed = runner.invoke(app, ["experiment", root, "close", "--project", str(project)])
    assert closed.exit_code == 0 and "missing:" in closed.output
    packet = runner.invoke(app, ["experiment", root, "packet", "--project", str(project)])
    assert packet.exit_code == 0 and "# Engagement packet" in packet.output
    reviewed = runner.invoke(app, ["experiment", root, "review", "--reviewer", "Sam",
                                   "--evidence", "4", "--necessity", "5", "--operational", "3",
                                   "--implementation", "3", "--risk", "4",
                                   "--reversibility", "4", "--contract-signable",
                                   "--question", "none", "--guess", "without"])
    assert reviewed.exit_code == 0, reviewed.output
    assert "quality 3.833" in reviewed.output
    report = runner.invoke(app, ["experiment", str(tmp_path / "engagements"), "report"])
    assert report.exit_code == 0 and "1 engagement(s)" in report.output
    template = runner.invoke(app, ["experiment", root, "template", "--out",
                                   str(tmp_path / "log.yaml")])
    assert template.exit_code == 0 and yaml.safe_load((tmp_path / "log.yaml").read_text())
    again = runner.invoke(app, ["experiment", root, "start", "--engineer", "Dev"])
    assert again.exit_code == 1 and "already in the experiment" in again.output
