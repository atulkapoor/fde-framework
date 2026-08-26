"""What has to be true before building is worth starting.

Five gates. Four block and accept an override with a recorded reason, because
an FDE on site can see things a checklist cannot. One does not: you can design
around a missing baseline, and you cannot design around credentials you do not
have. Waiting is the only move there, and pretending otherwise wastes weeks.
"""

import pytest

from fde.gates import (
    HardGate,
    completeness,
    input_status,
    validate_baseline,
)
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.models.respondent import Respondent


def profile(**values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    return p


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


# --- the baseline is seven fields, not a yes ------------------------------


def test_a_baseline_is_seven_fields_rather_than_a_boolean(reg=None):
    """'Do you have a baseline?' gets yes and nothing usable."""
    assert validate_baseline(GOOD_BASELINE).ok


def test_a_missing_field_names_itself(reg=None):
    partial = {k: v for k, v in GOOD_BASELINE.items() if k != "rework_rate"}
    result = validate_baseline(partial)
    assert not result.ok
    assert "rework_rate" in result.reason


def test_a_best_case_measurement_is_refused(reg=None):
    """Cycle time from the fastest run tells you what is possible, not what
    happens, and the gap between them is the whole project."""
    best_case = {**GOOD_BASELINE, "sampled": False}
    result = validate_baseline(best_case)
    assert not result.ok
    assert "representative" in result.reason


def test_a_baseline_nobody_can_repeat_is_refused(reg=None):
    """The test of a baseline: can the same fields be measured again by the
    same definitions in sixty days. Otherwise it is a number from a meeting."""
    vague = {**GOOD_BASELINE, "definitions_recorded": False}
    result = validate_baseline(vague)
    assert not result.ok
    assert "re-measur" in result.reason


def test_an_absent_baseline_offers_a_remedy_rather_than_only_failing(reg=None):
    """'You have no baseline' is unhelpful. 'Measure these seven for a month'
    is a task somebody can start today."""
    status = input_status(profile(), baseline=None)
    gate = status.gate("baseline_capture")
    assert not gate.passed
    assert "30" in gate.remedy and "60" in gate.remedy


# --- hard and soft --------------------------------------------------------


def test_data_access_cannot_be_overridden(reg=None):
    """You can design around a missing baseline. You cannot design around
    credentials you do not have -- you can only wait for them."""
    status = input_status(profile(), data_access=False)
    with pytest.raises(HardGate, match="data_access"):
        status.override("data_access", reason="we will sort it out later")
    assert not status.can_proceed


def test_a_soft_gate_takes_an_override_with_a_reason(reg=None):
    """The override clears that gate. Others may still stand, and saying which
    is more use than a single yes or no."""
    status = input_status(profile(), baseline=None)
    assert "baseline_capture" in status.blocked_by()
    status.override("baseline_capture", reason="client refuses; measuring post-hoc")
    assert "baseline_capture" not in status.blocked_by()


def test_everything_satisfied_means_proceed(reg=None):
    p = Profile()
    p.ingest([Fact("output_shape", "structured", Provenance.INTERVIEW,
                   respondent=Respondent(role="eval_owner", name="A")),
              Fact("hosting", "on-prem", Provenance.DETECTED,
                   respondent=Respondent(role="admin", name="B"))])
    status = input_status(p, baseline=GOOD_BASELINE, data_access=True)
    assert status.can_proceed
    assert status.blocked_by() == []


def test_an_override_without_a_reason_is_refused(reg=None):
    """A gate waved through with no reason is a gate that was not considered."""
    status = input_status(profile(), baseline=None)
    with pytest.raises(ValueError, match="reason"):
        status.override("baseline_capture", reason="")


def test_an_overridden_gate_is_recorded_for_the_risk_section(reg=None):
    status = input_status(profile(), baseline=None)
    status.override("baseline_capture", reason="client refuses")
    assert status.overridden[0].reason == "client refuses"


def test_working_data_access_passes_the_hard_gate(reg=None):
    assert input_status(profile(), data_access=True).gate("data_access").passed


# --- the scarcest respondent ----------------------------------------------


def test_a_missing_eval_owner_is_reported(reg=None):
    """Nobody who can say what good means. Everything downstream of that is
    unmeasurable, and it is the gap teams discover last."""
    status = input_status(profile())
    assert "eval_owner" in status.missing_roles
    assert not status.gate("client_readiness").passed


def test_an_eval_owner_who_has_spoken_satisfies_it(reg=None):
    p = Profile()
    p.ingest([Fact("output_shape", "structured", Provenance.INTERVIEW,
                   respondent=Respondent(role="eval_owner", name="A"))])
    assert input_status(p).gate("client_readiness").passed


# --- drift and offline evaluation ------------------------------------------


def test_scope_drift_is_measured_against_the_original_statement(reg=None):
    """Not against the current one. Measuring drift against the latest version
    is measuring nothing."""
    status = input_status(
        profile(),
        original_statement="Extract fields from supplier invoices.",
        current_statement="Extract fields, reconcile them, and file the return.",
    )
    assert not status.gate("scope_drift").passed
    assert "original" in status.gate("scope_drift").reason.lower()


def test_an_unchanged_statement_does_not_drift(reg=None):
    same = "Extract fields from supplier invoices."
    status = input_status(profile(), original_statement=same, current_statement=same)
    assert status.gate("scope_drift").passed


def test_an_air_gap_needs_a_metric_that_runs_inside_it(reg=None):
    """A metric that needs a hosted model is not a metric you have, and
    finding that out at deployment is finding it out too late."""
    status = input_status(profile(hosting="air-gapped", output_shape="freeform"))
    assert not status.gate("offline_evaluability").passed


def test_a_structured_output_is_evaluable_anywhere(reg=None):
    status = input_status(profile(hosting="air-gapped", output_shape="structured"))
    assert status.gate("offline_evaluability").passed


# --- how complete ----------------------------------------------------------


def test_completeness_counts_what_decisions_need_not_how_many_fields(reg=None):
    """Ten trivial answers is not 'mostly done'. The measure is how much of
    what gets decided is actually settled."""
    trivial = profile(external_systems=1, recall_span="within_turn")
    decisive = profile(output_shape="structured", data_residency="cannot_leave")
    assert completeness(decisive) > completeness(trivial)


def test_nothing_known_is_zero(reg=None):
    assert completeness(Profile()) == 0.0


def test_status_separates_what_is_known_from_what_is_assumed(reg=None):
    status = input_status(profile(output_shape="structured"))
    assert "output_shape" in status.known
    assert set(status.known) & set(status.missing) == set()


# --- as an FDE sees it -----------------------------------------------------


def test_status_shows_what_is_blocking(tmp_path):
    from typer.testing import CliRunner

    from fde.cli import app

    runner = CliRunner()
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    (tmp_path / "acme" / "facts" / "0001.yaml").write_text(
        "session_id: '0001'\nrespondent: {role: admin}\n"
        "facts:\n  - {dimension: output_shape, value: structured, provenance: artifact}\n"
    )
    result = runner.invoke(app, ["status", str(tmp_path / "acme")])
    assert "blocked by" in result.output
    assert "[hard]" in result.output


def test_the_hard_gate_is_marked_as_such(tmp_path):
    """An FDE reading this should be able to tell in one glance which of these
    is worth arguing about and which is worth waiting for."""
    from typer.testing import CliRunner

    from fde.cli import app

    runner = CliRunner()
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    (tmp_path / "acme" / "facts" / "0001.yaml").write_text(
        "session_id: '0001'\nrespondent: {role: admin}\n"
        "facts:\n  - {dimension: output_shape, value: structured, provenance: artifact}\n"
    )
    result = runner.invoke(app, ["status", str(tmp_path / "acme")])
    assert "[hard] data_access" in result.output


def test_status_reports_completeness_by_decision_weight(tmp_path):
    from typer.testing import CliRunner

    from fde.cli import app

    runner = CliRunner()
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    (tmp_path / "acme" / "facts" / "0001.yaml").write_text(
        "session_id: '0001'\nrespondent: {role: admin}\n"
        "facts:\n  - {dimension: external_systems, value: 1, provenance: artifact}\n"
    )
    result = runner.invoke(app, ["status", str(tmp_path / "acme")])
    assert "settled" in result.output
    assert "0%" in result.output or "2%" in result.output


# --- the registry is the source of truth ------------------------------------


def registry_with_dimension(tmp_path, body):
    from fde.registry import load_registry

    (tmp_path / "dimensions").mkdir(parents=True)
    (tmp_path / "dimensions" / "custom.md").write_text(body)
    return load_registry(tmp_path)


def test_a_new_decisive_dimension_needs_no_code_edit(tmp_path):
    """Weights live in the dimensions' own frontmatter. The hardcoded table
    went stale the day a dimension was added without editing it -- which is
    exactly what hardcoded tables do."""
    registry = registry_with_dimension(tmp_path, (
        "---\nid: custom\ntype: enum\nweight: 5.0\nvalues: [a, b]\n---\nbody\n"
    ))
    empty = completeness(profile(), registry)
    settled = completeness(profile(custom="a"), registry)
    assert empty == 0.0
    assert settled == 1.0


def test_the_boundary_gate_reads_the_registry(tmp_path):
    """A new value that forbids egress trips offline evaluability without a
    code change: boundary_when and needs_judge are content."""
    registry = registry_with_dimension(tmp_path, (
        "---\nid: custom\ntype: enum\nweight: 1.0\n"
        "values: [sovereign, open]\nboundary_when: [sovereign]\n"
        "needs_judge: [never]\n---\nbody\n"
    ))
    # add an output dimension declaring judged values
    (tmp_path / "dimensions" / "shape.md").write_text(
        "---\nid: shape\ntype: enum\nweight: 1.0\n"
        "values: [prose, table]\nneeds_judge: [prose]\n---\nbody\n"
    )
    from fde.registry import load_registry

    registry = load_registry(tmp_path)
    blocked = input_status(
        profile(custom="sovereign", shape="prose"), registry=registry
    )
    assert not blocked.gate("offline_evaluability").passed
    fine = input_status(
        profile(custom="open", shape="prose"), registry=registry
    )
    assert fine.gate("offline_evaluability").passed


def test_without_a_registry_the_gates_still_function(tmp_path):
    """The fallback exists so the gates work bare; it is expected to lag the
    registry, never to disagree with it on what it does cover."""
    status = input_status(profile(hosting="air-gapped", output_shape="freeform"))
    assert not status.gate("offline_evaluability").passed
