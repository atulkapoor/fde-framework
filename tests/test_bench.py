"""A bench is the same figures read off every record, side by side, and
says how many rows it has."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from fde.bench import measure, render
from fde.cli import app
from fde.factlog import load_engagement, start_engagement

runner = CliRunner()


def scored(tmp_path, name, holdout="77.5% on 3036 cases (majority 1.9%; abstained 10.5%, "
                                    "86.6% on the answered)"):
    start_engagement(tmp_path, name, statement="Route.")
    eng = load_engagement(tmp_path / name)
    (tmp_path / name / "lifecycle.jsonl").write_text(
        json.dumps({"at": "2026-09-01", "from": None, "stage": "discovery"}) + "\n"
        + json.dumps({"at": "2026-09-08", "from": "discovery", "stage": "pilot"}) + "\n")
    project = tmp_path / f"{name}-project"
    project.mkdir()
    (project / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "measured": holdout, "holds": True},
        {"property": "external exam", "measured": "75.8% on 3079 cases (majority 1.3%)",
         "holds": True},
        {"property": "generalisation gap", "measured": "golden 91.6% - holdout 77.5% = +14.2%",
         "holds": True},
        {"property": "lint", "measured": "clean", "holds": False},
        {"property": "training path", "measured": "none", "holds": None},
    ]}))
    return eng, project


def test_a_row_reads_the_card_and_the_trail(tmp_path):
    eng, project = scored(tmp_path, "acme")
    row = measure(eng, project)
    assert row["stage"] == "pilot" and row["card"] == "3/4"
    assert row["holdout"] == 0.775 and row["abstained"] == 0.105
    assert row["external"] == 0.758 and abs(row["gap"] - 0.142) < 1e-9
    assert row["days_to_pilot"] == 7 and row["incidents"] == "0 opened, 0 open"


def test_an_engagement_without_a_build_has_dashes(tmp_path):
    start_engagement(tmp_path, "bare", statement="Route.")
    row = measure(load_engagement(tmp_path / "bare"), None)
    assert row["stage"] == "unrecorded" and row["holdout"] is None
    text = render([row])
    assert "1 engagement(s)" in text and "| bare | unrecorded | -- | -- |" in text


def test_the_command_writes_the_table(tmp_path):
    _, project = scored(tmp_path, "acme")
    start_engagement(tmp_path, "bare", statement="Route.")
    out = tmp_path / "BENCH.md"
    result = runner.invoke(app, ["bench", f"{tmp_path / 'acme'}={project}",
                                 str(tmp_path / "bare"), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "2 engagement(s)" in out.read_text() and "| acme | pilot | 3/4 | 77.5% |" in \
        out.read_text()
