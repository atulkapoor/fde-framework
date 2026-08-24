"""Cheap first, escalate what fails -- and the residue is the learning queue.

Four separate lines of research describe one pattern. Entity resolution runs
deterministic rules for the confident subset and something else for the
remainder. Model cascades try the cheapest model and escalate on low confidence.
Active learning scores without labels and sends the least confident to a human.
Tiered memory keeps cheaply and promotes deliberately.

They are the same thing: do the cheap confident work, and treat what is left as
both the escalation path and the queue worth a human's attention.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from fde.architect import architect
from fde.emit import emit
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"

MIXED = dict(
    output_shape="structured", input_format="documents", query_pattern="lookup",
    corpus_size=200_000, labelled_count=8_000, data_residency="cannot_leave",
    hosting="air-gapped", latency_budget_ms=800, external_systems=3,
    recall_span="within_session", operates_after_handover="platform_team",
    confidence_calibrated=True, cheap_path_coverage=0.7,
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def profile(**values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    return p


@pytest.fixture(scope="module")
def built(reg, tmp_path_factory):
    out = tmp_path_factory.mktemp("cascade")
    emit(architect(profile(**MIXED), reg), out)
    return out


def run_in(project, code):
    return subprocess.run(
        [sys.executable, "-c", code], cwd=project, capture_output=True, text=True
    )


# --- the decision --------------------------------------------------------


def test_a_cascade_is_chosen_when_the_cheap_path_covers_only_part_of_the_work(reg):
    """Most records have an exact identifier; a minority do not. Rules alone
    would finish the ones they can and drop the rest quietly."""
    from fde.decide import decide_component

    assert decide_component("representation", MIXED, reg).approach == "cascade"


def test_rules_alone_win_when_they_cover_the_work(reg):
    """A second tier for the last two percent is machinery nobody needs."""
    from fde.decide import decide_component

    covered = {**MIXED, "cheap_path_coverage": 0.99}
    assert decide_component("representation", covered, reg).approach == "deterministic"


def test_a_cascade_is_refused_when_confidence_is_not_calibrated(reg):
    """Routing on a miscalibrated score is a cost saving with an unknown error
    rate attached. Better to run the reliable path over everything."""
    from fde.decide import decide_component

    uncalibrated = {**MIXED, "confidence_calibrated": False}
    assert decide_component("representation", uncalibrated, reg).approach != "cascade"


# --- the implementation --------------------------------------------------


def test_the_cheap_tier_handles_what_it_is_confident_about(built):
    result = run_in(built, """
from app.components.representation import Representation
r = Representation()
out = r.run({"records": [
    {"id": "1", "account": "GB29 1234", "name": "Acme Ltd"},
    {"id": "2", "account": "", "name": "acme limited"},
]})
assert out["resolved"][0]["tier"] == "exact"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_what_the_cheap_tier_cannot_settle_is_escalated_not_guessed(built):
    result = run_in(built, """
from app.components.representation import Representation
out = Representation().run({"records": [
    {"id": "2", "account": "", "name": "acme limited"},
]})
assert out["escalated"], "an unconfident record must escalate rather than be guessed at"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_the_escalated_records_are_the_verification_queue(built):
    """The same residue serves both purposes. Records the cheap path could not
    handle are exactly the ones worth a human's attention."""
    result = run_in(built, """
from app.components.representation import Representation
out = Representation().run({"records": [
    {"id": "1", "account": "GB29 1234", "name": "Acme Ltd"},
    {"id": "2", "account": "", "name": "???"},
]})
assert [r["id"] for r in out["verify_queue"]] == [r["id"] for r in out["escalated"]]
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_an_uncalibrated_threshold_is_refused_at_run_time_too(built):
    """Not only at decision time. A threshold nobody measured is a guess with a
    number written next to it."""
    result = run_in(built, """
from app.components.representation import Representation, Uncalibrated
r = Representation(calibrated=False)
try:
    r.run({"records": [{"id": "1", "account": "", "name": "x"}]})
except Uncalibrated as e:
    print("refused:", e)
else:
    raise AssertionError("routed on an uncalibrated score")
""")
    assert result.returncode == 0, result.stderr
    assert "refused" in result.stdout


def test_calibration_reports_what_the_threshold_actually_buys(built):
    """Cost saved is meaningless without the error rate it bought."""
    result = run_in(built, """
from app.components.representation import Representation
report = Representation().calibrate([
    {"confident": True,  "correct": True},
    {"confident": True,  "correct": False},
    {"confident": False, "correct": False},
])
assert "escalation_rate" in report and "cheap_tier_error_rate" in report
print(report)
""")
    assert result.returncode == 0, result.stderr


def test_the_cheap_tier_error_rate_is_measured_not_assumed(built):
    result = run_in(built, """
from app.components.representation import Representation
report = Representation().calibrate([{"confident": True, "correct": False}] * 10)
assert report["cheap_tier_error_rate"] == 1.0
assert report["safe"] is False, "a tier that is always wrong must not be trusted"
print("ok")
""")
    assert result.returncode == 0, result.stderr
