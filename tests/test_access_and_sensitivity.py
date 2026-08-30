"""The three deferred concerns, built: who may act, which fields would hurt,
and which candidate problem to start with.

Each earns its place the way the corpus demands: a decision depends on it,
or the gap checker would have refused it as an inert question.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fde.cli import app
from fde.decide import decide_component
from fde.decompose import decompose
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"
runner = CliRunner()


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def profile(**values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    return p


# --- access_model moves the governance decision -----------------------------


def test_role_based_access_selects_role_scoped_authority(reg):
    decision = decide_component("governance", {
        "access_model": "role_based", "data_residency": "may_leave",
    }, reg)
    assert decision.approach == "role-scoped-authority"


def test_one_operating_team_keeps_the_simple_audit(reg):
    decision = decide_component("governance", {
        "access_model": "single_operator", "data_residency": "may_leave",
    }, reg)
    assert decision.approach == "audit-only"


def test_unstated_access_changes_nothing(reg):
    """The invoice example and every existing engagement must decide exactly
    as before -- a new dimension nobody answered is a question, not a veto."""
    decision = decide_component("governance", {"data_residency": "cannot_leave"}, reg)
    assert decision.approach == "boundary-and-audit"


# --- field sensitivity earns a pipeline step, exactly in the crossed case ---


def test_sensitive_fields_that_may_leave_require_redaction(reg):
    components = decompose(profile(
        sensitivity_present=True, data_residency="may_leave",
        output_shape="structured", corpus_size=1000,
    ), reg).components
    assert "redaction" in components


def test_no_redaction_when_the_boundary_already_holds_everything(reg):
    components = decompose(profile(
        sensitivity_present=True, data_residency="cannot_leave",
        output_shape="structured", corpus_size=1000,
    ), reg).components
    assert "redaction" not in components


def test_redaction_decides_to_deterministic_masking(reg):
    decision = decide_component("redaction", {
        "sensitivity_present": True, "data_residency": "may_leave",
    }, reg)
    assert decision.approach == "deterministic-masking"


def test_redaction_runs_after_perception_and_before_representation(reg):
    """A mask applied after embedding is a mask applied to a copy."""
    from fde.decide import decide_all
    from fde.workflow import build_graph

    values = dict(sensitivity_present=True, data_residency="may_leave",
                  output_shape="structured", corpus_size=50_000,
                  labelled_count=0, input_format="documents")
    components = list(decompose(profile(**values), reg).components)
    graph = build_graph(decide_all(values, reg, components=components), reg,
                        values=values)
    order = [n.id for n in graph.ordered()]
    assert order.index("perception") < order.index("redaction")
    assert order.index("redaction") < order.index("representation")


# --- samples --sensitive: declared beats detected ---------------------------


def _engagement_with_pairs(tmp_path, sensitive=()):
    import json as jsonlib

    root = tmp_path / "eng"
    runner.invoke(app, ["start", "eng", "--base", str(tmp_path)])
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("".join(
        jsonlib.dumps({"id": str(i),
                       "input": {"narrative": f"text {i}", "patient": f"p{i}"},
                       "output": {"urgency": "urgent"}}) + "\n"
        for i in range(3)
    ))
    args = ["samples", str(root), "--file", str(pairs)]
    for field in sensitive:
        args += ["--sensitive", field]
    return root, runner.invoke(app, args)


def test_a_marked_field_is_recorded_and_raises_the_fact(tmp_path):
    root, result = _engagement_with_pairs(tmp_path, sensitive=["patient"])
    assert result.exit_code == 0
    assert (root / "artifacts" / "sensitive_fields.json").exists()
    status = runner.invoke(app, ["status", str(root), "--registry", str(FRAMEWORK)])
    assert "sensitivity_present = True" in status.output


def test_marking_a_field_the_pairs_do_not_have_is_refused(tmp_path):
    _, result = _engagement_with_pairs(tmp_path, sensitive=["ssn"])
    assert result.exit_code == 1
    assert "not fields in these pairs" in result.output


# --- triage: decidability ranked, honestly labelled -------------------------


def test_triage_ranks_the_described_candidate_first():
    result = runner.invoke(app, [
        "triage", "--registry", str(FRAMEWORK),
        "--statement", "Extract structured fields from 500k scanned documents; "
                       "data cannot leave and a person is waiting.",
        "--statement", "Make operations better with AI.",
    ])
    assert result.exit_code == 0
    first = result.output.split("1.")[1].split("2.")[0]
    assert "Extract" in first
    assert "decidability, not value" in result.output


def test_triage_refuses_a_single_candidate():
    result = runner.invoke(app, ["triage", "--registry", str(FRAMEWORK),
                                 "--statement", "just one"])
    assert result.exit_code == 1


def test_triage_flags_a_statement_bundling_two_workflows():
    result = runner.invoke(app, [
        "triage", "--registry", str(FRAMEWORK),
        "--statement", "An agent platform for two workflows: drafting research "
                       "notes, and surveilling trades for market abuse.",
        "--statement", "Read supplier invoices into the ledger.",
    ])
    assert "more than one workflow" in result.output
