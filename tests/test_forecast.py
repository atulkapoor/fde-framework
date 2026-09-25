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
                   project, by="Priya", at="2026-09-01", confidence=0.7)
    assert len(added) == 3 and not any(a["already_measured"] for a in added)
    assert added[0]["evidence"]["figures_measured"] == [] and added[0]["confidence"] == 0.7
    assert added[0]["evidence"]["card"] is None and added[0]["evidence"]["profile"]
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
    assert "at 70% confidence" in text and "calibration needs at least 5" in text
    assert (tmp_path / "acme" / "forecast-scores.jsonl").exists()


def test_a_forecast_about_a_figure_already_measured_is_marked_per_figure(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route.")
    eng = load_engagement(tmp_path / "acme")
    project = project_with_card(tmp_path)
    added = record(eng, ["holdout_accuracy >= 0.7", "field_abstain_rate <= 0.2"], project)
    assert added[0]["already_measured"] is True and added[1]["already_measured"] is False
    assert added[0]["evidence"]["card"] and "holdout_accuracy" in \
        added[0]["evidence"]["figures_measured"]
    text = render(evaluate(forecasts(eng), {"holdout_accuracy": 0.775}))
    assert text.count("[the figure was already on the record]") == 1


def test_a_confidence_is_a_share_and_calibration_waits_for_five(tmp_path):
    import pytest

    start_engagement(tmp_path, "acme", statement="Route.")
    eng = load_engagement(tmp_path / "acme")
    with pytest.raises(ValueError):
        record(eng, ["holdout_accuracy >= 0.7"], confidence=1.5)
    results = [{"condition": f"m{i} >= 0", "measured": 1.0, "held": i % 5 != 0, "error": 1.0,
                "already_measured": False, "confidence": 0.9, "by": ""} for i in range(10)]
    assert "held rate 80% against mean confidence 90% over 10" in render(results)


def test_the_command_records_judges_and_says_when_it_was_late(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route.")
    root = str(tmp_path / "acme")
    project = project_with_card(tmp_path)
    result = runner.invoke(app, ["predict", root, "--when", "holdout_accuracy >= 0.7",
                                 "--project", str(project), "--by", "Priya",
                                 "--confidence", "0.8"])
    assert result.exit_code == 0, result.output
    assert "recorded 1 forecast(s)" in result.output
    assert "already measured when forecast, kept and marked: holdout_accuracy >= 0.7" \
        in result.output
    assert "ok  holdout_accuracy >= 0.7" in result.output
    bad = runner.invoke(app, ["predict", root, "--when", "vibes good"])
    assert bad.exit_code == 1
    history = runner.invoke(app, ["history", root])
    assert "forecast " in history.output and "forecasts scored" in history.output
