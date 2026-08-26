"""Capturing what an engagement taught, so the next one can use it.

Capture now, revise later. Rules cannot be revised until engagements have
outcomes, so the revision genuinely belongs further out -- but a signal not
captured on the first engagement is gone, and the whole premise is that this
improves from use.

Three signals, in descending order of how much they are worth.

**Overrides** are strong: the FDE saw something the rules did not.
**Trigger calibration** is strong: predicted against observed, with no
counterfactual to argue about -- it either fired when we said or it did not.
**Replay** is weak and genuinely counterfactual, so a recommendation differing
from what was actually done is marked unresolved rather than counted.
"""

import hashlib
from pathlib import Path

from fde.evolution import (
    Observation,
    Override,
    Prediction,
    calibration,
    emit_case,
    replay_verdict,
    sweep_triggers,
)

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


def hash_of(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


# --- overrides -----------------------------------------------------------


def test_an_override_records_the_rule_it_overrode(reg=None):
    """Without knowing what was overridden the signal is unusable: 'they chose
    something else' does not tell you which rule was wrong."""
    override = Override(
        component="serving", recommended="self-hosted", chosen="managed-api",
        because="no GPU budget this quarter", overrode_rule="self-hosted",
    )
    assert override.overrode_rule == "self-hosted"


def test_an_override_is_never_a_warning(reg=None):
    """The FDE is on site and knows things the rules do not. Recording it is
    the point; arguing with it is not."""
    override = Override(
        component="serving", recommended="self-hosted", chosen="managed-api",
        because="client insists", overrode_rule="self-hosted",
    )
    assert override.blocking is False


def test_an_override_against_a_hard_constraint_is_flagged_not_refused(reg=None):
    override = Override(
        component="serving", recommended="self-hosted", chosen="managed-api",
        because="client insists", overrode_rule="self-hosted",
        conflicts_with=["data_residency=cannot_leave"],
    )
    assert override.conflicts_with
    assert override.blocking is False


# --- trigger calibration -------------------------------------------------


def test_a_trigger_records_a_dated_prediction_when_it_is_set(reg=None):
    """Without the prediction, 'did it fire when we said?' is unanswerable
    later, and later is the only time anybody asks."""
    prediction = Prediction(
        trigger="serving.rung_1", condition="p95_ms > 800",
        predicted_at="2026-08-25", horizon_days=90,
    )
    assert prediction.predicted_at and prediction.horizon_days


def test_a_firing_records_observed_against_predicted(reg=None):
    prediction = Prediction("serving.rung_1", "p95_ms > 800", "2026-08-25", 90)
    observation = Observation.fired(prediction, at="2026-09-10", measured={"p95_ms": 910})
    assert observation.status == "fired"
    assert observation.delta_days == 16


def test_a_trigger_that_never_fires_is_also_an_outcome(reg=None):
    """Silence is data. A trigger that never fires may be badly calibrated, and
    nobody finds out unless it is swept."""
    prediction = Prediction("serving.rung_1", "p95_ms > 800", "2026-08-25", 30)
    swept = sweep_triggers([prediction], observations=[], today="2026-11-01")
    assert swept[0].status == "expired_unfired"


def test_a_trigger_still_within_its_horizon_is_neither(reg=None):
    prediction = Prediction("serving.rung_1", "p95_ms > 800", "2026-08-25", 90)
    swept = sweep_triggers([prediction], observations=[], today="2026-09-01")
    assert swept[0].status == "pending"


def test_calibration_needs_no_counterfactual_and_says_so(reg=None):
    prediction = Prediction("a", "x > 1", "2026-08-25", 90)
    report = calibration([Observation.fired(prediction, "2026-09-10", {"x": 2})])
    assert report["strength"] == "strong"
    assert report["fired"] == 1


def test_calibration_reports_how_far_off_the_prediction_was(reg=None):
    prediction = Prediction("a", "x > 1", "2026-08-25", 30)
    report = calibration([Observation.fired(prediction, "2026-10-25", {"x": 2})])
    assert report["median_delta_days"] > 30
    assert report["well_calibrated"] is False


# --- replay --------------------------------------------------------------


def test_a_replay_that_agrees_with_what_was_done_is_evidence(reg=None):
    assert replay_verdict(recommended="deterministic", actual="deterministic")["verdict"] == (
        "agreed"
    )


def test_a_replay_that_disagrees_is_unresolved_rather_than_wrong(reg=None):
    """We recommended something else and it was not tried. Nobody knows what
    would have happened, and pretending otherwise is faking rigour."""
    verdict = replay_verdict(recommended="cascade", actual="deterministic")
    assert verdict["verdict"] == "unresolved"
    assert "not tried" in verdict["why"]


def test_replay_is_marked_weak(reg=None):
    assert replay_verdict("a", "b")["strength"] == "weak"


# --- the case record -----------------------------------------------------


def test_a_completed_engagement_emits_a_case(reg=None):
    """Without this every engagement is a dead end and nothing compounds."""
    case = emit_case(
        engagement="acme",
        profile={"output_shape": "structured", "data_residency": "cannot_leave"},
        decisions={"representation": "deterministic"},
        observations=[],
        outcome="delivered; extraction accuracy above target",
    )
    assert case["decisions"] and case["outcome"]


def test_the_case_is_sanitised_before_it_can_enter_the_corpus(reg=None):
    case = emit_case(
        engagement="Acme Financial Services",
        profile={"output_shape": "structured"},
        decisions={},
        observations=[],
        outcome="delivered",
    )
    assert "Acme" not in str(case)
    # Pending, never reviewed: the machine anonymises the id, but only a
    # person can say nothing identifying survives in the free-text fields,
    # and a case that claims review nobody did would sail past the gate
    # that keeps unsanitised material out of a public corpus.
    assert case["sanitization"] == "pending"


def test_the_case_records_which_predictions_were_wrong(reg=None):
    """A corpus of successes teaches less than one that admits what it got
    wrong, and the wrong ones are what revision needs."""
    prediction = Prediction("a", "x > 1", "2026-08-25", 30)
    case = emit_case(
        "acme", {}, {}, sweep_triggers([prediction], [], today="2026-11-01"), "delivered"
    )
    assert any(t["status"] == "expired_unfired" for t in case["triggers"])


def test_the_practice_metric_is_recorded(reg=None):
    """Time to build the Nth solution, and how much was reused. The denominator
    revision will eventually be measured against."""
    case = emit_case("acme", {}, {}, [], "delivered", days=21, reused=["pgvector"])
    assert case["practice"]["days"] == 21
    assert case["practice"]["reused"] == ["pgvector"]


# --- capture only --------------------------------------------------------


def test_capturing_changes_no_rules(reg=None):
    """Revision is a later phase. Pretending to revise on four engagements
    would be faking rigour, and the framework says so elsewhere."""
    before = hash_of(FRAMEWORK)
    emit_case("acme", {"a": 1}, {"b": "c"}, [], "delivered")
    calibration([])
    assert hash_of(FRAMEWORK) == before
