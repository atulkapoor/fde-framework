"""The deliverable-acceptance suite: the emitted project, held to the bar.

Every finding any audit makes about emitted output lands HERE as a check
before it lands anywhere as a fix -- so the bar is executable, applies to
every architecture shape, and never regresses. This is the same doctrine
the emitted projects live under, applied to the emitter itself.
"""

import re
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

# Representative shapes: extraction (no model), decision (tools/agent
# posture), freeform (model + retrieval + judge). New shapes join here.
SHAPES = {
    "extraction": dict(
        output_shape="structured", input_format="scanned_documents",
        query_pattern="lookup", corpus_size=200_000, labelled_count=10_000,
        data_residency="cannot_leave", hosting="on-prem", external_systems=3,
        human_waiting="yes", cheap_path_coverage=0.33,
        confidence_calibrated=False, interpretability_required=False),
    "decision": dict(
        output_shape="decision", input_format="text", corpus_size=5_000,
        data_residency="may_leave", hosting="customer-vpc",
        external_systems=3, human_waiting="no", query_pattern="lookup",
        recall_span="within_turn"),
    "freeform": dict(
        output_shape="freeform", input_format="text", corpus_size=40_000,
        data_residency="cannot_leave", hosting="on-prem",
        external_systems=2, human_waiting="no", query_pattern="lookup"),
}


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


@pytest.fixture(scope="module", params=sorted(SHAPES))
def emission(request, reg, tmp_path_factory):
    out = tmp_path_factory.mktemp(f"accept-{request.param}")
    profile = Profile()
    profile.ingest([Fact(k, v, Provenance.ARTIFACT)
                    for k, v in SHAPES[request.param].items()])
    emit(architect(profile, reg), out)
    return request.param, out


def emitted_env_vars(out: Path) -> set[str]:
    """Every environment variable any emitted python reads."""
    found = set()
    for py in out.rglob("*.py"):
        found |= set(re.findall(
            r"environ(?:\.get)?\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']", py.read_text()))
    return found - {"ANTHROPIC_API_KEY"}  # the hosted path's own contract


def test_every_env_var_the_code_reads_is_documented(emission):
    """A mandatory variable that appears in no document is discovered by
    the first user instead of the deploy -- the class of miss behind
    'LLM_ENDPOINT appears in no doc at all'."""
    shape, out = emission
    documented = (out / "deploy" / "env.example").read_text()
    undocumented = {v for v in emitted_env_vars(out) if v not in documented}
    assert not undocumented, (
        f"{shape}: emitted code reads {sorted(undocumented)} but "
        f"deploy/env.example never mentions them")


def test_the_runbook_gives_an_operator_their_first_commands(emission):
    """3am needs commands before doctrine: the health probe and the
    journal, at minimum, on the page the unit points an operator at."""
    shape, out = emission
    ops_text = " ".join(p.read_text() for p in (out / "ops").glob("*.md"))
    deploy_text = " ".join(p.read_text() for p in (out / "deploy").rglob("*.md"))
    everything = ops_text + deploy_text
    assert "/health" in everything or "curl" in everything, (
        f"{shape}: no operational command (health probe) in ops/ or deploy/ docs")
    assert "journalctl" in everything, (
        f"{shape}: journalctl appears nowhere an operator will look")


def test_everything_the_unit_demands_something_shipped_creates(emission):
    """A unit wanting /opt/app/.venv, user `app`, /var/lib/app and
    /etc/app/env, beside nothing that creates any of them, is a
    deliverable the first operator cannot install. Whatever provisioner
    was decided -- playbook or manual steps -- the creation path ships."""
    shape, out = emission
    unit = out / "deploy" / "systemd" / "app.service"
    if not unit.exists():
        pytest.skip("shape does not emit a systemd unit")
    site = out / "deploy" / "ansible" / "site.yml"
    installer = (site.read_text() if site.exists()
                 else (out / "deploy" / "README.md").read_text())
    for demand, evidence in [
        ("ExecStart interpreter", "venv"),
        ("installed package", "pip"),
        ("service account", "app"),
        ("writable state dir", "/var/lib/app"),
        ("environment file", "env"),
    ]:
        assert evidence in installer, (
            f"{shape}: the unit demands a {demand} and no shipped "
            f"installer creates it (looked for {evidence!r})")


def test_the_project_installs_and_its_smoke_test_passes(emission):
    """`pip install -e .` must work and the deliverable must carry a
    model-free unit smoke a maintainer can run in seconds."""
    shape, out = emission
    smoke = out / "tests" / "test_smoke.py"
    assert smoke.exists(), f"{shape}: no tests/test_smoke.py in the deliverable"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(smoke)],
        cwd=out, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        f"{shape}: the deliverable's own smoke test fails on a fresh "
        f"emission:\n{result.stdout[-800:]}{result.stderr[-400:]}")


def test_ci_has_a_lane_that_can_go_green_without_a_model(emission):
    """A committed workflow that can never pass is a permanent red X
    teaching everyone to ignore CI. The smoke lane gates every push; a
    judged evaluation joins only where a model is configured."""
    shape, out = emission
    ci = (out / ".github" / "workflows" / "ci.yml").read_text()
    assert "test_smoke.py" in ci, (
        f"{shape}: no model-free smoke lane in the workflow")
    if shape == "freeform":  # judged evaluation -- needs a model
        assert "if: ${{ vars.LLM_ENDPOINT != '' }}" in ci, (
            f"{shape}: the judged harness runs unconditionally and can "
            f"never pass without a model")
    else:
        assert "harness.py" in ci, (
            f"{shape}: the model-free evaluation was dropped from CI")


def test_advisory_components_say_they_are_advisory(emission):
    """A component that is decided-on-record but not wired into the
    payload path must say so in its own docstring -- silence reads as
    running."""
    shape, out = emission
    pipeline = (out / "app" / "pipeline.py").read_text()
    wired = set(re.findall(r"components import (\w+)", pipeline)) | set(
        re.findall(r"\(\s*['\"](\w+)['\"]\s*,", pipeline))
    for module in (out / "app" / "components").glob("*.py"):
        if module.stem in ("__init__",) or module.stem in wired:
            continue
        body = module.read_text()
        if "raise" in body.split("\n\n")[0]:
            continue  # undecided scaffolds announce themselves already
        assert "advisory" in body[:1500].lower() or "build time" in body[:1500].lower(), (
            f"{shape}: {module.name} is not wired into the pipeline and its "
            f"docstring does not say it is advisory")
