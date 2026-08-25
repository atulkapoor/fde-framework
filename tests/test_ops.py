"""What somebody needs at three in the morning, and what CI needs at merge.

A runbook that repeats the architecture is not a runbook. What is wanted is:
here is what you will see, here is what it means, here is what to do. And a
rollback document that says "revert the deployment" is lying if the system sent
anything, charged anything or wrote anything downstream.
"""

from pathlib import Path

import pytest

from fde.architect import architect
from fde.emit import emit
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"

BASE = dict(
    output_shape="structured", input_format="documents", query_pattern="lookup",
    corpus_size=200_000, latency_budget_ms=800, external_systems=2,
    recall_span="within_session", operates_after_handover="platform_team",
    cheap_path_coverage=0.99,
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def build(reg, out, **values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in {**BASE, **values}.items()])
    emit(architect(p, reg), out)
    return out


@pytest.fixture(scope="module")
def project(reg, tmp_path_factory):
    return build(reg, tmp_path_factory.mktemp("ops"),
                 hosting="on-prem", container_competence=False, provisioning_api=False,
                 external_systems=1)


# --- the runbook ---------------------------------------------------------


def test_the_runbook_pairs_symptoms_with_actions(project):
    """Not a description of the system. What you will see, what it means, what
    to do about it."""
    body = (project / "ops" / "runbook.md").read_text()
    assert body.count("**You see**") >= 3
    assert body.count("**Do**") >= 3


def test_every_error_source_has_an_entry(project):
    """The taxonomy classifies failures by source. The runbook is what makes
    that classification worth having."""
    body = (project / "ops" / "runbook.md").read_text()
    for source in ("data", "input", "prediction", "output", "system", "integration"):
        assert source in body.lower()


def test_the_runbook_names_the_components_that_are_actually_there(project):
    body = (project / "ops" / "runbook.md").read_text()
    assert "perception" in body


def test_it_says_where_to_look_first(project):
    """Quality flows one direction. The earliest capping component is the
    answer to 'the answers are wrong and I do not know why'."""
    body = (project / "ops" / "runbook.md").read_text()
    assert "perception" in body and "first" in body.lower()


# --- service objectives --------------------------------------------------


def test_both_metric_buckets_appear(project):
    """A technical number nobody outside the team cares about, and a business
    number nobody inside it can move directly. Reporting one is half a story."""
    body = (project / "ops" / "slo.md").read_text()
    assert "Technical" in body and "Business" in body


def test_the_latency_objective_comes_from_the_stated_budget(project):
    assert "800" in (project / "ops" / "slo.md").read_text()


def test_a_missing_baseline_is_stated_rather_than_left_blank(project):
    """Without one there is nothing to compare against, and that is a finding
    rather than an empty section."""
    body = (project / "ops" / "slo.md").read_text()
    assert "baseline" in body.lower()
    assert "not captured" in body.lower() or "no baseline" in body.lower()


def test_the_objectives_are_re_measurable(project):
    """The test of an objective: can the same fields be measured again in sixty
    days by the same definition."""
    assert "60 days" in (project / "ops" / "slo.md").read_text()


# --- rollback ------------------------------------------------------------


def test_rollback_is_commands_not_advice(project):
    assert "```bash" in (project / "ops" / "rollback.md").read_text()


def test_rollback_matches_the_substrate_that_was_chosen(project):
    assert "systemctl" in (project / "ops" / "rollback.md").read_text()


def test_it_names_what_rolling_back_does_not_undo(project):
    """The part that makes it honest. Reverting a deployment does not unsend an
    email, unmake a payment or unwrite a row downstream."""
    body = (project / "ops" / "rollback.md").read_text()
    assert "does not" in body.lower()
    assert "irreversible" in body.lower()


def test_a_container_deployment_gets_container_commands(reg, tmp_path):
    out = build(reg, tmp_path, hosting="on-prem", container_competence=True,
                provisioning_api=False)
    assert "compose" in (out / "ops" / "rollback.md").read_text()


# --- continuous integration ----------------------------------------------


def test_ci_gates_on_the_evaluation_not_only_on_unit_tests(project):
    """A pipeline that runs pytest and calls it quality has not measured the
    thing the system is for."""
    body = (project / ".github" / "workflows" / "ci.yml").read_text()
    assert "evals/harness.py" in body
    assert "--min-score" in body


def test_ci_asserts_the_boundary(reg, tmp_path):
    out = build(reg, tmp_path, hosting="air-gapped", data_residency="cannot_leave",
                container_competence=False, provisioning_api=False, external_systems=1)
    assert "boundary" in (out / ".github" / "workflows" / "ci.yml").read_text()


def test_ci_runs_the_adversarial_layer_too(project):
    """Scoring well on golden and badly on adversarial is not a good system.
    It is one nobody has attacked."""
    assert "adversarial" in (project / ".github" / "workflows" / "ci.yml").read_text()
