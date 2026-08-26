"""Profiles the registry must serve, and honesty about the ones it cannot.

`find_gaps` counts approaches per component. None of that says whether an
approach can *fire* for a given set of honest answers -- which is how three
quarters of fully specified profiles once had an undecidable required
component while the gap report read zero.
"""

from pathlib import Path

import pytest

from fde.decide import decide_component
from fde.graph import sweep_dead_zones
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


# --- zones that were dead and must not be ----------------------------------


def test_a_no_container_team_can_still_deploy(reg):
    """Three integrations and no container practice once blocked all three
    deployment approaches at once. The floor cannot be knocked out by
    workload shape."""
    decision = decide_component("deployment", {
        "container_competence": False, "external_systems": 3,
        "existing_cluster": False,
    }, reg)
    assert decision.approach == "systemd-unit"


def test_a_cluster_shop_deploys_to_its_cluster_regardless_of_this_team(reg):
    """An existing cluster means somebody operates it. Blocking manifests on
    the applying team's skills left a cluster shop with no deployment at all."""
    decision = decide_component("deployment", {
        "container_competence": False, "existing_cluster": True,
        "external_systems": 3,
    }, reg)
    assert decision.approach == "kubernetes-manifests"


def test_a_decision_shaped_system_has_an_evaluation(reg):
    decision = decide_component("evaluation", {"output_shape": "decision"}, reg)
    assert decision.approach == "labelled-metrics"


def test_unmeasured_structured_extraction_reaches_a_model(reg):
    """The flagship case, before anyone has measured anything: the cascade
    needs calibration that does not exist and the deterministic path needs
    coverage nobody counted. The opening move is a model decoding into the
    schema -- not silence."""
    decision = decide_component("reasoning", {
        "output_shape": "structured", "confidence_calibrated": False,
        "cheap_path_coverage": 0.5,
    }, reg)
    assert decision.approach == "llm"


def test_supervised_approaches_ask_whether_labels_exist(reg):
    """finetune and classical-ml literally cannot work without labels, and
    neither used to test the one dimension that says whether any exist."""
    without = decide_component("reasoning", {
        "output_shape": "classification", "labelled_count": 0,
    }, reg)
    assert without.approach != "classical-ml"
    with_labels = decide_component("representation", {
        "output_shape": "classification", "labelled_count": 50_000,
    }, reg)
    assert with_labels.approach == "classical-ml"


def test_a_tight_latency_budget_rules_out_a_remote_endpoint(reg):
    """The budget dimension now decides something: sub-100ms cannot be met
    across somebody else's network, which is physics rather than pricing."""
    decision = decide_component("serving", {
        "output_shape": "freeform", "data_residency": "may_leave",
        "latency_budget_ms": 50, "human_waiting": "yes",
    }, reg)
    assert decision.approach != "managed-api"


# --- honesty where no approach can fire ------------------------------------


def test_a_true_conflict_is_named_not_blamed_on_ignorance(reg):
    """Everything known, every approach ruled out: saying 'not enough is
    known' sends somebody to ask questions that cannot help."""
    decision = decide_component("embedding", {
        "data_residency": "cannot_leave", "operates_after_handover": "nobody_yet",
        "corpus_size": 100_000, "query_pattern": "semantic",
        "output_shape": "structured", "hosting": "on-prem",
    }, reg)
    assert decision.approach is None
    assert "conflict" in decision.rationale
    assert "not enough" not in decision.rationale
    assert "cannot_leave" in decision.rationale


def test_missing_answers_are_still_reported_as_missing(reg):
    decision = decide_component("serving", {"output_shape": "freeform"}, reg)
    if decision.approach is None:
        assert "unanswered" in decision.rationale


# --- the sweep -------------------------------------------------------------


def test_the_sweep_is_deterministic(reg):
    a = sweep_dead_zones(reg, samples=40, seed=7)
    b = sweep_dead_zones(reg, samples=40, seed=7)
    assert a == b


def test_every_reported_example_really_is_undecidable(reg):
    """The sweep's evidence must reproduce: a dead-zone report whose example
    decides fine on replay is noise wearing a finding's clothes."""
    result = sweep_dead_zones(reg, samples=60, seed=3)
    for component, entry in result["dead"].items():
        assert decide_component(component, entry["example"], reg).approach is None


def test_the_common_deployment_paths_are_alive(reg):
    """The most frequent real-world shapes must not appear in the dead list
    for deployment: the sweep may find exotic conflicts, but a plain team
    with or without a cluster always has a rung."""
    for profile in (
        {"container_competence": False, "existing_cluster": False, "external_systems": 3},
        {"container_competence": True, "existing_cluster": False, "external_systems": 0},
        {"container_competence": False, "existing_cluster": True, "external_systems": 5},
    ):
        assert decide_component("deployment", profile, reg).approach is not None
