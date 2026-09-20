"""The eighth gate: nobody builds until somebody has agreed which number
the system exists to move, from what to what, measured how, by when."""

from __future__ import annotations

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement, start_engagement
from fde.gates import input_status, validate_outcome_contract
from fde.lifecycle import assess
from fde.models.profile import Profile

runner = CliRunner()

CONTRACT = {"owner": "AP director", "metric": "invoice_processing_time",
            "baseline": {"value": 300, "unit": "s"}, "target": {"value": 120, "unit": "s"},
            "method": "the AP dashboard's monthly median", "window": "90 days after go-live"}


def test_a_contract_is_six_fields_and_two_numbers():
    assert validate_outcome_contract(CONTRACT).ok
    assert "no outcome contract" in validate_outcome_contract(None).reason
    partial = dict(CONTRACT, target=None)
    assert "lacks target" in validate_outcome_contract(partial).reason
    prose = dict(CONTRACT, baseline={"value": "three hundred", "unit": "s"})
    assert "baseline is not a number" in validate_outcome_contract(prose).reason
    empty = dict(CONTRACT, method="   ")
    assert "method says nothing" in validate_outcome_contract(empty).reason


def test_the_gate_blocks_without_a_contract_and_names_the_remedy():
    status = input_status(Profile(), baseline=None, data_access=True)
    gate = status.gate("outcome_contract")
    assert not gate.passed and "which number" in gate.reason
    assert "fde outcome-contract" in gate.remedy and not gate.hard
    assert "outcome_contract" in status.blocked_by()
    passing = input_status(Profile(), outcome_contract=CONTRACT)
    assert passing.gate("outcome_contract").passed


def test_the_gate_is_waivable_with_a_reason():
    status = input_status(Profile())
    status.override("outcome_contract", "the client will set the target after the pilot")
    assert "outcome_contract" not in status.blocked_by()


def test_the_command_records_and_the_status_reads_it(tmp_path):
    start_engagement(tmp_path, "acme", statement="Extract invoice fields.")
    root = str(tmp_path / "acme")
    result = runner.invoke(app, ["outcome-contract", root, "--owner", "AP director",
                                 "--metric", "invoice_processing_time", "--baseline", "300",
                                 "--unit", "s", "--target", "120",
                                 "--method", "the AP dashboard's monthly median",
                                 "--window", "90 days after go-live", "--by", "Priya Rao"])
    assert result.exit_code == 0, result.output
    assert "outcome contract recorded" in result.output
    contract = load_engagement(tmp_path / "acme").outcome_contract()
    assert contract["metric"] == "invoice_processing_time" and contract["by"] == "Priya Rao"
    assert contract["baseline"] == {"value": 300.0, "unit": "s"}
    status = runner.invoke(app, ["status", root])
    assert "outcome_contract" not in status.output.split("blocked by")[-1].split("\n")[0]


def test_an_incomplete_contract_is_recorded_and_said_to_be_incomplete(tmp_path):
    start_engagement(tmp_path, "acme", statement="Extract invoice fields.")
    root = str(tmp_path / "acme")
    result = runner.invoke(app, ["outcome-contract", root, "--owner", "AP director",
                                 "--metric", "cycle"])
    assert result.exit_code == 0
    assert "incomplete" in result.output and "lacks" in result.output
    status = runner.invoke(app, ["status", root])
    assert "outcome_contract" in status.output


def test_the_adoption_stage_reads_the_contracted_metric(tmp_path):
    start_engagement(tmp_path, "acme", statement="Extract invoice fields.")
    eng = load_engagement(tmp_path / "acme")
    eng.record_outcome_contract(CONTRACT)
    life = assess(eng, blocked_gates=[], project=None)
    adoption = next(s for s in life.stages if s.name == "adoption")
    assert "invoice_processing_time" in adoption.criteria[0].name
    assert "--metric invoice_processing_time=" in adoption.criteria[0].evidence
    (tmp_path / "acme" / "outcomes.jsonl").write_text(
        '{"metric": "invoice_processing_time", "value": 140, "at": "2026-12-01"}\n')
    life = assess(eng, blocked_gates=[], project=None)
    adoption = next(s for s in life.stages if s.name == "adoption")
    assert adoption.holds and "target 120" in adoption.criteria[0].evidence
