"""Forecasts go on the record before the score and are judged after it;
one written after a card existed is kept, and marked."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement, start_engagement
from fde.forecast import evaluate, forecasts, record, render, score

runner = CliRunner()
HOLDOUT = "77.5% on 3036 cases (majority 1.9%; abstained 10.5%, 86.6% on the answered)"


def project_with_card(tmp_path):
    project = tmp_path / "project"
    (project / "evals").mkdir(parents=True)
    (project / "evals" / "manifest.json").write_text("{}")
    (project / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "measured": HOLDOUT, "holds": True}]}))
    return project


def test_a_forecast_before_the_score_is_judged_after_it(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route.")
    eng = load_engagement(tmp_path / "acme")
    project = tmp_path / "project"
    (project / "evals").mkdir(parents=True)
    added = record(eng, ["holdout_accuracy >= 0.8", "abstain_rate <= 0.2", "adoption >= 0.5"],
                   project, by="Priya", at="2026-09-01")
    assert len(added) == 3 and not any(a["after_scoring"] for a in added)
    assert record(eng, ["holdout_accuracy >= 0.8"], project) == []  # not twice
    (project / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "measured": HOLDOUT, "holds": True}]}))
    results = score(eng, project, at="2026-09-20")
    by = {r["condition"]: r for r in results}
    assert by["holdout_accuracy >= 0.8"]["held"] is False
    assert by["holdout_accuracy >= 0.8"]["error"] == -0.025
    assert by["abstain_rate <= 0.2"]["held"] is True
    assert by["adoption >= 0.5"]["held"] is None
    text = render(results)
    assert "MISS  holdout_accuracy >= 0.8" in text and "error -0.025" in text
    assert "3 forecast(s): 1 held, 1 missed, 1 not measured" in text
    assert (tmp_path / "acme" / "forecast-scores.jsonl").exists()


def test_a_forecast_after_a_card_exists_is_marked(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route.")
    eng = load_engagement(tmp_path / "acme")
    project = project_with_card(tmp_path)
    added = record(eng, ["holdout_accuracy >= 0.7"], project)
    assert added[0]["after_scoring"] is True
    assert "[made after a card existed]" in render(evaluate(forecasts(eng),
                                                            {"holdout_accuracy": 0.775}))


def test_the_command_records_judges_and_says_when_it_was_late(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route.")
    root = str(tmp_path / "acme")
    project = project_with_card(tmp_path)
    result = runner.invoke(app, ["predict", root, "--when", "holdout_accuracy >= 0.7",
                                 "--project", str(project), "--by", "Priya"])
    assert result.exit_code == 0, result.output
    assert "recorded 1 forecast(s)" in result.output
    assert "made after a card existed" in result.output
    assert "ok  holdout_accuracy >= 0.7" in result.output
    bad = runner.invoke(app, ["predict", root, "--when", "vibes good"])
    assert bad.exit_code == 1
    history = runner.invoke(app, ["history", root])
    assert "forecast " in history.output and "forecasts scored" in history.output
