"""The business-value engine: the client's own figures and the scorecard's
out-of-sample rows, every line labelled by what it rests on."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement, start_engagement
from fde.value import estimate, render

runner = CliRunner()

BASELINE = {
    "volume": {"value": 10000, "unit": "messages/month",
               "definition": "inbound messages needing a queue (stated by the support lead)"},
    "cycle_time_per_unit_seconds": {"value": 45, "unit": "s",
                                    "definition": "read to queue assigned, measured on 200 cases"},
    "labour_hours_per_week": {"value": 30, "unit": "h/week", "definition": "stated"},
    "error_rate": {"value": 0.12, "unit": "share", "definition": "re-routes, measured on a week"},
}
ROWS = {"holdout": {"property": "holdout", "holds": True,
                    "measured": "77.5% on 3036 cases (majority 1.9%; abstained 10.5%, "
                                "86.6% on the answered)"}}


def test_every_line_says_what_it_rests_on():
    value = estimate(BASELINE, ROWS, hourly_cost=40, implementation_hours=160,
                     monthly_run_cost=500)
    by = {line.name: line for line in value.lines}
    assert by["annual volume"].value == 120000 and by["annual volume"].basis == "stated"
    assert by["human hours today"].basis == "measured"
    assert by["automated share"].value == 0.895 and by["automated share"].basis == "measured"
    assert by["accuracy on the automated"].value == 0.866
    assert by["residual human share"].value == 0.105
    assert by["hours saved"].value == round(120000 * 45 / 3600 * 0.895)
    assert by["errors a person made on the same items"].basis == "measured"
    assert by["net errors"].value == round(120000 * 0.895 * (1 - 0.866) - 120000 * 0.895 * 0.12)
    assert by["cost to build"].basis == "assumed" and by["cost to run"].value == 6000
    assert by["payback"].unit == "months" and 0 < by["payback"].value < 6
    assert "Wilson" in by["accuracy interval"].note


def test_review_share_is_an_assumption_that_reduces_the_saving():
    plain = estimate(BASELINE, ROWS, hourly_cost=40, implementation_hours=160,
                     monthly_run_cost=500)
    reviewed = estimate(BASELINE, ROWS, hourly_cost=40, implementation_hours=160,
                        monthly_run_cost=500, review_share=0.5)
    assert reviewed.get("hours saved") < plain.get("hours saved")
    review = next(line for line in reviewed.lines
                  if line.name == "human review of automated items")
    assert review.basis == "assumed"


def test_without_a_holdout_row_nothing_is_valued():
    value = estimate(BASELINE, None, hourly_cost=40, implementation_hours=160,
                     monthly_run_cost=500)
    assert value.get("automated share") is None
    assert "run fde scorecard --holdout" in next(
        line for line in value.lines if line.name == "automated share").note


def test_a_saving_that_does_not_cover_the_run_cost_has_no_payback():
    value = estimate(BASELINE, ROWS, hourly_cost=1, implementation_hours=10,
                     monthly_run_cost=5000)
    assert value.get("payback") is None


def test_the_document_names_the_stated_and_assumed_lines():
    value = estimate(BASELINE, ROWS, hourly_cost=40, implementation_hours=160,
                     monthly_run_cost=500)
    text = render(value, "acme")
    assert "Stated, not measured: annual volume" in text
    assert "Assumed by the caller: hourly cost" in text
    assert "| automated share | 0.895 |" in text


def test_the_value_command_writes_beside_the_project(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route each message.")
    eng = load_engagement(tmp_path / "acme")
    eng.record_baseline(BASELINE)
    project = tmp_path / "project"
    project.mkdir()
    (project / "scorecard.json").write_text(json.dumps({"rows": list(ROWS.values())}))
    result = runner.invoke(app, ["value", str(tmp_path / "acme"), "--project", str(project),
                                 "--hourly-cost", "40"])
    assert result.exit_code == 0, result.output
    assert (project / "VALUE.md").exists() and "payback" in result.output
