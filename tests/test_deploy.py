"""How it runs, and who applies it.

Neither containers nor Terraform is a default here. Both are the answer often
enough to be reached for reflexively and wrong often enough that reaching
reflexively is expensive -- a single-node deployment for a team with no
container competence does not want Kubernetes, and a shop that lives in Ansible
does not want Terraform however clean the HCL.
"""

from pathlib import Path

import pytest

from fde.architect import architect
from fde.decide import decide_component
from fde.emit import emit
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def profile(**values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    return p


BASE = dict(
    output_shape="structured", input_format="documents", query_pattern="lookup",
    corpus_size=200_000, latency_budget_ms=800, external_systems=2,
    recall_span="within_session", operates_after_handover="platform_team",
    cheap_path_coverage=0.99,
)


# --- the substrate is a ladder, not a default ----------------------------


def test_a_team_without_container_experience_gets_a_service_unit(reg):
    """Rung zero is a real answer. Adding containers here adds a permanent
    competency requirement to a team that did not ask for one."""
    decision = decide_component(
        "deployment",
        dict(hosting="on-prem", container_competence=False, external_systems=1),
        reg,
    )
    assert decision.approach == "systemd-unit"


def test_a_team_that_runs_containers_gets_containers(reg):
    decision = decide_component(
        "deployment",
        dict(hosting="on-prem", container_competence=True, external_systems=2),
        reg,
    )
    assert decision.approach in {"compose", "kubernetes-manifests"}


def test_an_existing_cluster_is_used_rather_than_avoided(reg):
    """Reuse-first applies to platforms too. A cluster already being operated
    is cheaper than anything standing beside it."""
    decision = decide_component(
        "deployment",
        dict(hosting="customer-vpc", container_competence=True, existing_cluster=True),
        reg,
    )
    assert decision.approach == "kubernetes-manifests"


def test_kubernetes_is_not_reached_for_without_a_cluster_or_a_reason(reg):
    decision = decide_component(
        "deployment",
        dict(hosting="on-prem", container_competence=True, existing_cluster=False,
             external_systems=1),
        reg,
    )
    assert decision.approach != "kubernetes-manifests"


# --- who applies it ------------------------------------------------------


def test_a_shop_that_lives_in_ansible_gets_ansible(reg):
    """Team competence outranks tool taxonomy. They operate this after we
    leave, and handing an Ansible shop Terraform is a disservice however clean
    the HCL."""
    decision = decide_component(
        "provisioning",
        dict(hosting="customer-vpc", existing_iac_tool="ansible"),
        reg,
    )
    assert decision.approach == "ansible-playbook"


def test_bare_metal_with_no_api_to_call_does_not_get_terraform(reg):
    """Somebody racked it. There is no lifecycle to manage and no API to
    manage it through, so a state file tracks zero resources."""
    decision = decide_component(
        "provisioning",
        dict(hosting="on-prem", provisioning_api=False),
        reg,
    )
    assert decision.approach != "terraform-module"


def test_an_environment_that_must_vanish_needs_a_tool_that_can_destroy(reg):
    """The one thing a converger genuinely cannot do."""
    decision = decide_component(
        "provisioning",
        dict(hosting="customer-vpc", provisioning_api=True,
             environment_lifetime="ephemeral"),
        reg,
    )
    assert decision.approach == "terraform-module"


def test_an_existing_cluster_needs_neither_provisioning_tool(reg):
    """The infrastructure is somebody else's problem. The application is
    manifests, and adding a provisioner is provisioning nothing."""
    decision = decide_component(
        "provisioning",
        dict(hosting="customer-vpc", existing_cluster=True, provisioning_api=True),
        reg,
    )
    assert decision.approach == "gitops"


# --- what gets written ---------------------------------------------------


def build(reg, out, **values):
    emit(architect(profile(**{**BASE, **values}), reg), out)
    return out


def test_a_service_unit_deployment_writes_no_dockerfile(reg, tmp_path):
    out = build(reg, tmp_path, hosting="on-prem", container_competence=False,
                provisioning_api=False, external_systems=1)
    assert (out / "deploy" / "systemd" / "app.service").exists()
    assert not (out / "Dockerfile").exists()


def test_a_container_deployment_writes_one(reg, tmp_path):
    out = build(reg, tmp_path, hosting="on-prem", container_competence=True,
                provisioning_api=False)
    assert (out / "Dockerfile").exists()


def test_images_are_pinned_by_digest_rather_than_a_moving_tag(reg, tmp_path):
    out = build(reg, tmp_path, hosting="on-prem", container_competence=True,
                provisioning_api=False)
    body = (out / "Dockerfile").read_text()
    assert ":latest" not in body


def test_an_air_gapped_build_references_no_public_registry(reg, tmp_path):
    out = build(reg, tmp_path, hosting="air-gapped", container_competence=True,
                data_residency="cannot_leave", provisioning_api=False)
    for path in (out / "deploy").rglob("*"):
        if path.is_file():
            assert "docker.io" not in path.read_text()
            assert "registry.terraform.io" not in path.read_text()


def test_teardown_is_written_whatever_the_substrate(reg, tmp_path):
    """An FDE who cannot cleanly undo a demo has a problem. Where the tool has
    no destroy, the manual steps are written out rather than left implied."""
    out = build(reg, tmp_path, hosting="on-prem", container_competence=False,
                provisioning_api=False, external_systems=1)
    teardown = out / "deploy" / "TEARDOWN.md"
    assert teardown.exists()
    assert "```" in teardown.read_text()


def test_the_deploy_directory_says_which_decisions_produced_it(reg, tmp_path):
    out = build(reg, tmp_path, hosting="on-prem", container_competence=False,
                provisioning_api=False, external_systems=1)
    assert "systemd-unit" in (out / "deploy" / "README.md").read_text()


# --- every registry approach has an emission path --------------------------


def test_a_manual_runbook_shop_gets_a_runbook(reg, tmp_path):
    """manual-runbook was in the registry with no branch in the emitter, so
    an engagement that decided it got an empty deploy/ and no complaint."""
    from fde.deploy import write_deploy

    architecture = architect(profile(
        **BASE, hosting="on-prem", provisioning_api=False,
        environment_lifetime="permanent", existing_iac_tool="none",
        existing_cluster=False, container_competence=False,
    ), reg)
    if architecture.decisions.get("provisioning") is None or \
            architecture.decisions["provisioning"].approach != "manual-runbook":
        pytest.skip("this profile no longer decides manual-runbook")
    write_deploy(architecture, tmp_path)
    runbook = tmp_path / "deploy" / "runbook.md"
    assert runbook.exists()
    assert "runbook that lies" in runbook.read_text()


def test_every_decided_provisioning_approach_emits_something(reg, tmp_path):
    """The registry can grow an approach faster than the emitter grows a
    branch. Whatever is decided, deploy/ must not be silently empty of it."""
    from fde.decide import Decision, Decisions
    from fde.deploy import write_deploy
    from fde.workflow import build_graph

    for approach in ("terraform-module", "ansible-playbook", "gitops",
                     "manual-runbook", "future-thing"):
        out = tmp_path / approach
        decisions = Decisions({
            "provisioning": Decision("provisioning", approach, "forced"),
            "deployment": Decision("deployment", "systemd-unit", "forced"),
        })
        architecture = architect(profile(**BASE), reg)
        architecture.decisions = decisions
        architecture.graph = build_graph(decisions, reg)
        write_deploy(architecture, out)
        emitted = [p.name for p in (out / "deploy").rglob("*") if p.is_file()]
        markers = {
            "terraform-module": "main.tf",
            "ansible-playbook": "site.yml",
            "gitops": "gitops.md",
            "manual-runbook": "runbook.md",
            "future-thing": "UNEMITTED-provisioning.md",
        }
        assert markers[approach] in emitted, (approach, emitted)


def test_the_air_gapped_terraform_module_carries_its_mirror(reg, tmp_path):
    """Air-gapped means no registry to reach; the module must say where
    providers come from instead."""
    from fde.decide import Decision, Decisions
    from fde.deploy import write_deploy
    from fde.workflow import build_graph

    decisions = Decisions({
        "provisioning": Decision("provisioning", "terraform-module", "forced"),
    })
    architecture = architect(profile(**BASE, hosting="air-gapped"), reg)
    architecture.decisions = decisions
    architecture.graph = build_graph(decisions, reg)
    write_deploy(architecture, tmp_path)
    body = (tmp_path / "deploy" / "terraform" / "main.tf").read_text()
    assert "filesystem_mirror" in body
    assert (tmp_path / "deploy" / "terraform" / "vendor").is_dir()
