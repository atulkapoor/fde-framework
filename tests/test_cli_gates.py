"""The gates, wired to a user.

Before this existed the gate module was a status display: no command could
satisfy a gate, none could waive one, and build never looked. A gate that
cannot pass, cannot be waved through and does not block is not a gate.
"""

import yaml
from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement

runner = CliRunner()

GOOD_BASELINE = {
    "volume": 200_000,
    "cycle_time_per_unit_seconds": 420,
    "labour_hours_per_week": 60,
    "rework_rate": 0.12,
    "exception_rate": 0.08,
    "error_rate": 0.05,
    "business_metric": "days to close a quarter",
    "sampled": True,
    "definitions_recorded": True,
}


def engagement(tmp_path, statement="Extract fields from statements."):
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path), "--statement", statement])
    return tmp_path / "acme"


def baseline_file(tmp_path, fields=None):
    path = tmp_path / "baseline.yaml"
    path.write_text(yaml.safe_dump(fields or GOOD_BASELINE))
    return path


def satisfy_all(tmp_path, root):
    runner.invoke(app, ["baseline", str(root), "--file", str(baseline_file(tmp_path))])
    runner.invoke(app, ["data-access", str(root),
                        "--note", "ran a query against the replica, 14 rows back"])
    runner.invoke(app, ["waive", str(root), "client_readiness",
                        "--reason", "eval owner starts Monday"])


# --- recording gate inputs -------------------------------------------------


def test_a_recorded_baseline_satisfies_the_gate(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["baseline", str(root), "--file", str(baseline_file(tmp_path))])
    assert "recorded" in result.output
    status = runner.invoke(app, ["status", str(root)])
    assert "baseline_capture" not in status.output


def test_a_partial_baseline_is_stored_and_named_incomplete(tmp_path):
    """Partial is honest state. The gate says what it still lacks."""
    root = engagement(tmp_path)
    partial = {k: v for k, v in GOOD_BASELINE.items() if k != "rework_rate"}
    result = runner.invoke(
        app, ["baseline", str(root), "--file", str(baseline_file(tmp_path, partial))]
    )
    assert "not yet a baseline" in result.output
    assert "rework_rate" in result.output
    status = runner.invoke(app, ["status", str(root)])
    assert "baseline_capture" in status.output


def test_data_access_needs_evidence_in_the_note(tmp_path):
    """An attestation without evidence is a promise, and promises are what
    the gate exists to refuse."""
    root = engagement(tmp_path)
    result = runner.invoke(app, ["data-access", str(root), "--note", "   "])
    assert result.exit_code == 1


def test_recorded_data_access_clears_the_hard_gate(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["data-access", str(root), "--note", "5 rows from the prod replica"])
    status = runner.invoke(app, ["status", str(root)])
    assert "[hard] data_access" not in status.output


# --- waiving ---------------------------------------------------------------


def test_a_soft_gate_can_be_waived_and_the_reason_survives(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["waive", str(root), "baseline_capture",
                        "--reason", "client refuses; measuring post-hoc"])
    status = runner.invoke(app, ["status", str(root)])
    assert "client refuses" in status.output
    assert load_engagement(root).gate_state()["overrides"][0]["gate"] == "baseline_capture"


def test_the_hard_gate_refuses_a_waiver(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["waive", str(root), "data_access",
                                 "--reason", "we will sort it out later"])
    assert result.exit_code == 1
    assert "cannot be overridden" in result.output


def test_a_waiver_without_a_reason_is_refused(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["waive", str(root), "baseline_capture", "--reason", "  "])
    assert result.exit_code == 1


def test_an_unknown_gate_lists_the_real_ones(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["waive", str(root), "vibes", "--reason", "because"])
    assert result.exit_code == 1
    assert "data_access" in result.output


def test_a_hand_edited_hard_waiver_does_not_take(tmp_path):
    """Editing gates.yaml around the rule leaves the gate standing, visibly."""
    root = engagement(tmp_path)
    (root / "gates.yaml").write_text(
        yaml.safe_dump({"overrides": [{"gate": "data_access", "reason": "trust me"}]})
    )
    status = runner.invoke(app, ["status", str(root)])
    assert "[hard] data_access" in status.output


# --- enforcement -----------------------------------------------------------


def test_build_refuses_while_gates_are_blocked(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["build", str(root), "--out", str(tmp_path / "out")])
    assert result.exit_code == 1
    assert "data_access" in result.output
    assert not (tmp_path / "out").exists()


def test_build_proceeds_once_gates_are_satisfied_or_waived(tmp_path):
    root = engagement(tmp_path)
    satisfy_all(tmp_path, root)
    result = runner.invoke(app, ["build", str(root), "--out", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "ARCHITECTURE.md").exists()


def test_architect_warns_but_still_thinks(tmp_path):
    """A design is thinking, not a deliverable. Refusing to even show one
    while waiting for credentials gets the framework worked around."""
    root = engagement(tmp_path)
    result = runner.invoke(app, ["architect", str(root)])
    assert result.exit_code == 0
    assert "data_access" in result.output
    assert "topology" in result.output


# --- scope drift, now live -------------------------------------------------


def test_restating_the_problem_makes_drift_measurable(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["restate", str(root),
                        "--text", "Extract fields, reconcile them, and file the return.",
                        "--reason", "sponsor added reconciliation in week two"])
    status = runner.invoke(app, ["status", str(root)])
    assert "scope_drift" in status.output


def test_a_restatement_without_a_reason_is_refused(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["restate", str(root), "--text", "Do more things."])
    assert result.exit_code == 1


def test_version_one_survives_restatement(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["restate", str(root), "--text", "Broader scope.",
                        "--reason", "sponsor request"])
    engagement_after = load_engagement(root)
    assert engagement_after.original_statement().text == "Extract fields from statements."
    assert engagement_after.current_statement().text == "Broader scope."
