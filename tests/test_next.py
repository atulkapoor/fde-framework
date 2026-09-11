"""`fde next`: the gates' remedy pattern, generalized to the lifecycle.

A refusal that names its remedy gets followed; a success that names
nothing strands the user at the exact moment they were moving. The
ladder below is the demonstration engagement's own arc, replayed as
assertions: gate, exam, questions, build, implement -- one move each.
"""

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from fde.cli import app

FRAMEWORK = str(Path(__file__).resolve().parents[1] / "framework")

runner = CliRunner()

FULL_FACTS = """session_id: '0001'
respondent: {role: admin}
facts:
  - {dimension: output_shape, value: structured, provenance: artifact}
  - {dimension: input_format, value: scanned_documents, provenance: artifact}
  - {dimension: corpus_size, value: 626, provenance: artifact}
  - {dimension: labelled_count, value: 626, provenance: artifact}
  - {dimension: data_residency, value: cannot_leave, provenance: artifact}
  - {dimension: hosting, value: on-prem, provenance: artifact}
  - {dimension: accelerator, value: none, provenance: artifact}
  - {dimension: access_model, value: single_operator, provenance: artifact}
  - {dimension: availability_target, value: business_hours, provenance: artifact}
  - {dimension: corpus_churn, value: continuous, provenance: artifact}
  - {dimension: environment_lifetime, value: permanent, provenance: artifact}
  - {dimension: existing_iac_tool, value: none, provenance: artifact}
  - {dimension: licence_posture, value: internal_only, provenance: artifact}
  - {dimension: operates_after_handover, value: app_team, provenance: artifact}
  - {dimension: recall_span, value: within_turn, provenance: artifact}
  - {dimension: arrival_rate, value: 40, provenance: artifact}
  - {dimension: human_waiting, value: "yes", provenance: artifact}
  - {dimension: latency_budget_ms, value: 30000, provenance: artifact}
  - {dimension: external_systems, value: 1, provenance: artifact}
  - {dimension: container_competence, value: false, provenance: artifact}
  - {dimension: existing_cluster, value: false, provenance: artifact}
  - {dimension: provisioning_api, value: false, provenance: artifact}
  - {dimension: cheap_path_coverage, value: 0.33, provenance: artifact}
  - {dimension: confidence_calibrated, value: false, provenance: artifact}
  - {dimension: interpretability_required, value: false, provenance: artifact}
  - {dimension: sensitivity_present, value: false, provenance: artifact}
  - {dimension: query_pattern, value: lookup, provenance: artifact}
"""


@pytest.fixture
def engagement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["start", "acme"])
    root = tmp_path / "engagements" / "acme"
    (root / "facts" / "0001.yaml").write_text(FULL_FACTS)
    return tmp_path


def nxt(args=("next", "acme")):
    result = runner.invoke(app, [*args, "--registry", FRAMEWORK])
    assert result.exit_code == 0, result.output
    return result.output


def clear_gates(tmp_path):
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text(yaml.safe_dump({
        "volume": 850, "cycle_time_per_unit_seconds": 180,
        "labour_hours_per_week": 20, "rework_rate": 0.08,
        "exception_rate": 0.05, "error_rate": 0.03,
        "business_metric": "days", "sampled": True,
        "definitions_recorded": True,
    }))
    runner.invoke(app, ["baseline", "acme", "--file", str(baseline)])
    runner.invoke(app, ["data-access", "acme", "--note", "626 real rows"])
    runner.invoke(app, ["waive", "acme", "client_readiness", "--reason", "demo"])
    runner.invoke(app, ["security-review", "acme", "--note", "self-review"])


def test_an_unsatisfied_gate_is_always_the_move(engagement):
    out = nxt()
    assert "fde data-access acme" in out
    assert "gate data_access" in out


def test_after_the_gates_the_exam_is_the_move(engagement):
    clear_gates(engagement)
    assert "fde samples acme" in nxt()


def test_after_the_exam_the_build_is_the_move(engagement):
    clear_gates(engagement)
    pairs = engagement / "pairs.jsonl"
    with pairs.open("w") as f:
        for i in range(45):
            f.write(json.dumps({"id": f"p{i}", "verified": True,
                                "input": f"receipt {i}",
                                "output": {"total": str(i)}}) + "\n")
    runner.invoke(app, ["samples", "acme", "--file", str(pairs)])
    assert "fde build acme" in nxt()


def test_after_the_build_the_implement_loop_is_the_move(engagement):
    clear_gates(engagement)
    root = engagement / "engagements" / "acme"
    (root / "artifacts").mkdir(exist_ok=True)
    (root / "artifacts" / "pairs.jsonl").write_text(
        json.dumps({"id": "p0", "verified": True, "input": "r",
                    "output": {"total": "1"}}) + "\n")
    (root / "predictions.jsonl").write_text("{}\n")
    (root / "artifacts" / "holdout.jsonl").write_text("{}\n")
    out = nxt()
    assert "fde implement project" in out
    assert "--holdout" in out


def test_recording_commands_name_the_next_move(engagement):
    # The footer needs a resolvable registry; without one it stays silent
    # rather than breaking the command it decorates.
    (engagement / "framework").symlink_to(Path(FRAMEWORK))
    result = runner.invoke(app, ["data-access", "acme", "--note", "rows"])
    assert "next:" in result.output


def test_an_undecided_component_keeps_the_ask_rung_alive(engagement):
    """Remove the query answer and retrieval cannot decide -- the ladder
    asks, and names what the answer would unblock."""
    clear_gates(engagement)
    root = engagement / "engagements" / "acme"
    facts = (root / "facts" / "0001.yaml").read_text()
    # Freeform puts retrieval in scope; without the query shape it cannot
    # decide, and the ladder must ask rather than build a raising module.
    facts = facts.replace("value: structured", "value: freeform")
    (root / "facts" / "0001.yaml").write_text(
        "\n".join(line for line in facts.splitlines() if "query_pattern" not in line))
    # Waive AFTER the facts change: a waiver is bound to the state it was
    # granted against, and one recorded before the shape flip would not
    # cover the gate that now fires.
    runner.invoke(app, ["waive", "acme", "offline_evaluability",
                        "--reason", "local judge planned"])
    (root / "artifacts").mkdir(exist_ok=True)
    (root / "artifacts" / "pairs.jsonl").write_text(
        '{"id": "p0", "verified": true, "input": "r", "output": {"total": "1"}}\n')
    out = nxt()
    assert "fde ask" in out and "undecided" in out


def test_an_unanswerable_question_does_not_trap_the_ladder(engagement):
    """cheap_path_coverage honestly unmeasured is the flagship case: every
    component still decides, so the move is build -- not the same question
    forever."""
    clear_gates(engagement)
    root = engagement / "engagements" / "acme"
    facts = (root / "facts" / "0001.yaml").read_text()
    (root / "facts" / "0001.yaml").write_text(
        "\n".join(line for line in facts.splitlines() if "cheap_path_coverage" not in line))
    (root / "artifacts").mkdir(exist_ok=True)
    (root / "artifacts" / "pairs.jsonl").write_text(
        '{"id": "p0", "verified": true, "input": "r", "output": {"total": "1"}}\n')
    assert "fde build acme" in nxt()
