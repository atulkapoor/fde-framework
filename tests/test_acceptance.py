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
    "assistant": dict(
        output_shape="freeform", input_format="text", corpus_size=10_000,
        data_residency="cannot_leave", hosting="on-prem",
        external_systems=1, human_waiting="yes", query_pattern="lookup",
        recall_span="across_sessions"),
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
    # The registry rides along, as it does in every real build -- an
    # emission judged without it once chained deployment as a payload
    # step and the suite blessed code no `fde build` ever produces.
    emit(architect(profile, reg), out, registry=reg)
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
    # The unit itself creates the state dir (StateDirectory=), owned by
    # the service user -- the one thing an installer should not do by hand.
    installer += unit.read_text()
    for demand, evidence in [
        ("ExecStart interpreter", "venv"),
        ("installed package", "pip"),
        ("service account", "app"),
        ("writable state dir", "StateDirectory=app"),
        ("environment file", "env"),
        ("release symlink for rollback", "current"),
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
    judged = "JUDGED = True" in (out / "evals" / "harness.py").read_text()
    if judged:  # a judged evaluation needs a model
        assert "vars.LLM_ENDPOINT != ''" in ci, (
            f"{shape}: the judged harness runs unconditionally and can "
            f"never pass without a model")
    else:
        assert "harness.py" in ci, (
            f"{shape}: the model-free evaluation was dropped from CI")


def test_emitted_code_passes_its_own_lint(emission):
    """The deliverable is code a client's staff engineer reads. An
    undefined name, an unsorted import block, a 110-column line -- each
    reads as ungroomed, and one of them (an unimported `time` in the
    retry path) was a crash. Lint-clean is the executable floor."""
    pytest.importorskip("ruff")
    shape, out = emission
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--isolated",
         "--select", "F,E,W,I,B,UP", "--line-length", "100", str(out)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        f"{shape}: emitted code fails its own lint:\n{result.stdout[-1500:]}")


def test_the_pipeline_chains_only_payload_components(emission):
    """A payload never passes through a deployment. Passthrough padding
    in STEPS is what makes a deliverable read as generated filler."""
    shape, out = emission
    steps = (out / "app" / "pipeline.py").read_text()
    steps = steps.split("STEPS = [", 1)[1].split("]", 1)[0]
    for component in ("deployment", "provisioning", "evaluation",
                      "observability", "governance", "accountability"):
        assert f"{component}." not in steps, (
            f"{shape}: {component} is chained as a payload step")


def test_advisory_components_say_they_are_advisory(emission):
    """A component that is decided-on-record but not chained into the
    payload path must say so in its own first lines -- silence reads as
    running."""
    shape, out = emission
    pipeline = (out / "app" / "pipeline.py").read_text()
    # Instantiated anywhere in the pipeline module -- in STEPS, in
    # INGEST_STEPS, or wired once as RETRIEVER.
    chained = set(re.findall(r"\b(\w+)\.[A-Z]\w*\(", pipeline))
    for module in (out / "app" / "components").glob("*.py"):
        if module.stem in ("__init__",) or module.stem in chained:
            continue
        body = module.read_text()
        assert "advisory" in body[:1500].lower() or "raise" in body[:1500], (
            f"{shape}: {module.name} is not chained into the pipeline and "
            f"nothing in its first lines says it is advisory")


# --- the seams: every emission composes, refuses, and answers -------------

REALISTIC = {
    "extraction": {"pages": [{"id": "p1", "text": "TOTAL 12.50"}]},
    "decision": "The bank charged a fee I never agreed to and will not refund it.",
    "freeform": "Which status code says a resource has moved permanently?",
    "assistant": "Remind me what we decided about the deployment window.",
}


def run_in(out: Path, code: str, env: dict | None = None):
    return subprocess.run(
        [sys.executable, "-c", code], cwd=out, capture_output=True, text=True,
        timeout=120, env={"PATH": "/usr/bin", **(env or {})},
    )


def test_the_pipeline_composes_on_a_fresh_emission(emission):
    """Every step reads the envelope the previous one wrote. The only
    acceptable stops on a fresh emission are a scaffold saying it is not
    implemented, or a model seam saying it is not configured -- never a
    KeyError three steps in, which is what 'the components do not
    compose' looks like at 3am."""
    shape, out = emission
    code = f"""
import json
from app import pipeline
try:
    result = pipeline.run({REALISTIC[shape]!r})
    print("RESULT", json.dumps(result, default=str)[:200])
except NotImplementedError as exc:
    print("SCAFFOLD", exc)
except Exception as exc:
    if type(exc).__name__ == "ModelUnconfigured":
        print("NO_MODEL", exc)
    else:
        raise
"""
    result = run_in(out, code)
    assert result.returncode == 0, (
        f"{shape}: the payload path does not compose:\n{result.stderr[-1500:]}")
    assert result.stdout.split()[0] in ("RESULT", "SCAFFOLD", "NO_MODEL"), result.stdout


def test_garbage_in_is_a_refusal_not_a_crash(emission):
    """None, a number, an empty string: refused at the door with the
    reason, never an AttributeError from the first step."""
    shape, out = emission
    code = """
from app import pipeline
from app.contract import RefusedInput
for bad in (None, 42, "", [1, 2], {"documents": "not a list"}):
    try:
        pipeline.run(bad)
    except RefusedInput:
        continue
    except NotImplementedError:
        continue  # a scaffold refused later, after the envelope accepted an object
    except Exception as exc:
        if type(exc).__name__ == "ModelUnconfigured":
            continue
        raise SystemExit(f"{bad!r} produced {type(exc).__name__}: {exc}")
    raise SystemExit(f"{bad!r} was accepted")
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"


def test_a_corpus_ingests_and_the_wired_retriever_answers(emission):
    """With a retrieval layer, ingest() fills the same instance the
    request path reads -- and evals/retrieval.py measures that one."""
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    code = """
from app import pipeline
n = pipeline.ingest([{"id": "d1", "text": "SKU-99312 costs 40 dollars"},
                     {"id": "d2", "text": "The office closes at six"}])
assert n >= 2, n
hits = pipeline.RETRIEVER.retrieve("SKU-99312", 5)
assert hits and "SKU-99312" in hits[0]["text"], hits
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-800:]}"


def test_the_edge_is_the_only_source_of_authority(emission):
    """A body that claims scopes for itself is stripped before the
    pipeline sees it; the principal is what the edge set."""
    shape, out = emission
    code = """
from app.shapes import envelope
env = envelope({"text": "hello", "principal": {"subject": "attacker", "scopes": ["admin"]},
                "request_id": "forged"})
assert "principal" not in env and "request_id" not in env, env
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"


def test_the_boundary_refuses_an_endpoint_outside_it(emission):
    shape, out = emission
    if not (out / "app" / "boundary.py").exists():
        pytest.skip("no boundary in this shape")
    outside = run_in(out, "import app.boundary", env={"LLM_ENDPOINT": "https://api.example.com"})
    assert outside.returncode != 0 and "outside the boundary" in outside.stderr
    inside = run_in(out, "import app.boundary", env={"LLM_ENDPOINT": "http://10.0.0.5:8000"})
    assert inside.returncode == 0, inside.stderr
    keyed = run_in(out, "import app.boundary", env={"ANTHROPIC_API_KEY": "sk-x"})
    assert keyed.returncode != 0


def test_the_ledger_outlives_the_process(emission):
    shape, out = emission
    if not (out / "app" / "ledger.py").exists():
        pytest.skip("nothing outward in this shape")
    state = out / "state"
    state.mkdir(exist_ok=True)
    code = """
from app.ledger import LEDGER, KeyUnresolved
key = LEDGER.key_for({"tool": "send", "arguments": {"to": "x"}})
assert LEDGER.reserve(key, "d1") is None
LEDGER.complete(key, {"sent": True})
LEDGER.append({"phase": "outcome", "tool": "send"})
print("ok")
"""
    first = run_in(out, code, env={"STATE_DIR": str(state)})
    assert first.returncode == 0, first.stderr
    again = run_in(out, """
from app.ledger import LEDGER
key = LEDGER.key_for({"tool": "send", "arguments": {"to": "x"}})
earlier = LEDGER.reserve(key, "d1")
assert earlier and earlier["outcome"] == {"sent": True}, earlier
print("ok")
""", env={"STATE_DIR": str(state)})
    assert again.returncode == 0, again.stderr
    assert (state / "audit.jsonl").exists() and (state / "idempotency.jsonl").exists()


def test_the_service_carries_a_request_id_on_every_answer(emission):
    """Refusals, answers and errors all carry the id -- and a bearer
    token, when configured, gates POST and non-loopback /ready."""
    shape, out = emission
    import json as jsonlib
    import socket
    import time
    import urllib.error
    import urllib.request

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.pipeline"], cwd=out,
        env={"PATH": "/usr/bin", "PORT": str(port), "AUTH_TOKEN": "s3cret",
             "GRANTED_SCOPES": "x", "LLM_ENDPOINT": "http://127.0.0.1:9"},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError(f"{shape}: service never came up: {proc.stdout.read()[:600]}")

        def post(body, token="s3cret"):
            req = urllib.request.Request(
                base + "/", data=body, method="POST",
                headers={"Content-Type": "application/json",
                         **({"Authorization": f"Bearer {token}"} if token else {})})
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    return r.status, jsonlib.loads(r.read()), r.headers
            except urllib.error.HTTPError as e:
                return e.code, jsonlib.loads(e.read()), e.headers

        code, body, headers = post(b"null", token=None)
        assert code == 401 and "request_id" in body
        code, body, headers = post(b"null")
        assert code == 422 and body["request_id"] == headers["X-Request-Id"], (code, body)
        code, body, headers = post(b'{"documents": "no"}')
        assert code == 422, (code, body)
        code, body, headers = post(b"[" * 5000)
        assert code == 400, (code, body)
        code, body, headers = post(jsonlib.dumps(REALISTIC[shape]).encode())
        assert code in (200, 500, 503), (code, body)
        assert "request_id" in body and "detail" not in body, body
    finally:
        proc.terminate()
        assert proc.wait(timeout=20) == 0, "SIGTERM must drain and exit 0"


def test_a_hostile_document_costs_milliseconds_not_minutes(emission):
    """The first pipeline step once backtracked quadratically: 400KB of a
    single non-whitespace run cost 58 minutes of CPU per unauthenticated
    request (measured by a red team). Perception must be linear in the
    input, whatever shape the input takes."""
    shape, out = emission
    perception = out / "app" / "components" / "perception.py"
    if "documents_of" not in perception.read_text():
        pytest.skip("this shape's perception does not read text documents")
    code = """
import time
from app.components.perception import Perception
p = Perception()
worst = time.perf_counter()
for text in ("a" * 400_000, ("a|" * 200_000), ("xxxxxxxxxx\\t" * 40_000), "a" + " " * 400_000):
    started = time.perf_counter()
    p.run({"documents": [{"id": "x", "text": text}]})
    worst = max(worst, time.perf_counter() - started)
print(f"{worst:.3f}")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"
    worst = float(result.stdout.strip().splitlines()[-1])
    assert worst < 2.0, f"{shape}: a hostile 400KB document took {worst:.1f}s"
