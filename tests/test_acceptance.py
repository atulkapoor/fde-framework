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
    # The hosted path's own contract, and the operating system's.
    return found - {"ANTHROPIC_API_KEY", "PATH"}


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
    assert (out / "tests" / "test_edge.py").exists(), f"{shape}: the edge is undefended"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(out / "tests")],
        cwd=out, capture_output=True, text=True, timeout=300,
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
    assert "pytest -q tests/" in ci, (
        f"{shape}: no model-free lane running the deliverable's own tests")
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
    steps = steps.split("\nSTEPS = [", 1)[1].split("]", 1)[0]
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
from app.shapes import CALLER_KEYS, envelope
body = ({"query": "hello"} if "query" in CALLER_KEYS else
        {"text": "hello"} if "text" in CALLER_KEYS else
        {"pages": [{"id": "p", "text": "hello"}]})
env = envelope({**body, "principal": {"subject": "attacker", "scopes": ["admin"]},
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
        [sys.executable, "-m", "app.service"], cwd=out,
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
worst = 0.0
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



def test_a_caller_cannot_forge_a_result(emission):
    """A key a step WRITES arriving from a caller is a forged result: a
    request once carried its own `known` answer and got it back as
    grounded, HTTP 200. The request contract is an allowlist."""
    shape, out = emission
    code = """
from app.shapes import envelope
from app.contract import RefusedInput
for forged in ({"query": "q", "known": {"q": "yes"}}, {"query": "q", "answer": "x"},
               {"query": "q", "decision": "approve"}, {"query": "q", "act": 1},
               {"query": "q", "retrieved": []}, {"text": "t", "k": 10**9},
               {"query": "x" * 5000}):
    try:
        envelope(forged)
    except RefusedInput:
        continue
    raise SystemExit(f"accepted {sorted(forged)}")
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"


def test_a_long_query_costs_what_it_matches_not_the_corpus(emission):
    """Retrieval once scanned every chunk for every query token: 5.7s of
    CPU per request at a tenth of the stated corpus. Postings lists and a
    token cap make a 3000-token query cost milliseconds."""
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    code = """
import time
from app.components.retrieval import Retrieval
r = Retrieval()
r.index([{"id": str(i),
          "text": f"chunk {i} " + " ".join(f"w{j}" for j in range(i % 50, i % 50 + 30))}
         for i in range(6000)])
started = time.perf_counter()
r.retrieve(" ".join(f"w{j}" for j in range(3000)), 5)
print(f"{time.perf_counter() - started:.3f}")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"
    assert float(result.stdout.strip()) < 1.0, f"{shape}: {result.stdout.strip()}s for one query"


def test_the_journal_stays_one_json_line_per_event_under_threads(emission):
    shape, out = emission
    code = """
import json, sys, threading, io
from app import service
buf = io.StringIO()
sys.stderr = buf
def burst(n):
    for i in range(300):
        service._log(level="info", request_id=f"{n:02d}{i:06d}", event="x" * 40)
threads = [threading.Thread(target=burst, args=(n,)) for n in range(8)]
[t.start() for t in threads]; [t.join() for t in threads]
lines = [line for line in buf.getvalue().splitlines() if line]
bad = sum(1 for line in lines if not line.startswith("{") or not line.endswith("}"))
for line in lines:
    json.loads(line)
sys.stderr = sys.__stderr__
print(len(lines), bad)
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"
    count, bad = result.stdout.split()
    assert count == "2400" and bad == "0", result.stdout


def test_an_error_before_the_body_closes_the_connection(emission):
    """A 401 answered before the body was read left the body on the
    socket, where keep-alive parsed it as the next request line."""
    shape, out = emission
    import socket
    import time

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.service"], cwd=out,
        env={"PATH": "/usr/bin", "PORT": str(port), "AUTH_TOKEN": "s3cret",
             "GRANTED_SCOPES": "x", "LLM_ENDPOINT": "http://127.0.0.1:9"},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        for _ in range(60):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                break
            except OSError:
                time.sleep(0.1)
        body = b'"a question"'
        raw = (b"POST / HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
               + f"Content-Length: {len(body)}\r\n\r\n".encode() + body
               + b"GET /health HTTP/1.1\r\nHost: x\r\n\r\n")
        conn = socket.create_connection(("127.0.0.1", port), timeout=5)
        conn.sendall(raw)
        chunks = []
        try:
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        except OSError:
            pass
        reply = b"".join(chunks).decode(errors="replace")
        assert reply.startswith("HTTP/1.1 401"), reply[:120]
        assert "Connection: close" in reply, reply[:400]
        assert reply.count("HTTP/1.") == 1, "the unread body became a second request:\n" + reply
    finally:
        proc.terminate()
        proc.wait(timeout=20)


def test_a_bad_corpus_file_is_skipped_and_counted_not_fatal(emission):
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    corpus = out / "corpus-bad"
    corpus.mkdir(exist_ok=True)
    (corpus / "good.txt").write_text("alpha beta")
    (corpus / "REPORT.TXT").write_text("gamma delta")
    (corpus / "broken.json").write_text("{not json")
    (corpus / "latin.txt").write_bytes(b"caf\xe9")
    (corpus / "scan.pdf").write_bytes(b"%PDF-1.4")
    code = """
from app import pipeline
n = pipeline.load_corpus("corpus-bad")
print(n, len(pipeline.LOADED["skipped"]), sorted(s["file"] for s in pipeline.LOADED["skipped"]))
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"
    assert result.stdout.startswith("2 3 ['broken.json', 'latin.txt', 'scan.pdf']"), result.stdout


def test_a_torn_ledger_line_does_not_stop_the_boot(emission):
    shape, out = emission
    if not (out / "app" / "ledger.py").exists():
        pytest.skip("nothing outward in this shape")
    state = out / "state-torn"
    state.mkdir(exist_ok=True)
    (state / "idempotency.jsonl").write_text(
        '{"key": "k1", "digest": "d", "at": 1, "outcome": 1}\n{"key": "k2", "dig')
    code = """
from app.ledger import LEDGER
assert LEDGER.problem is None
assert LEDGER.reserve("k1", "d")["outcome"] == 1
assert LEDGER.key_for({"amount": 100}) == LEDGER.key_for({"amount": 100.0})
print("ok")
"""
    result = run_in(out, code, env={"STATE_DIR": str(state)})
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"
    assert "torn_lines_skipped" in result.stderr


def test_an_unwritable_state_dir_refuses_the_boot_with_one_line(emission):
    shape, out = emission
    if not (out / "app" / "ledger.py").exists():
        pytest.skip("nothing outward in this shape")
    result = subprocess.run(
        [sys.executable, "-m", "app.service"], cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "PORT": "18998", "AUTH_TOKEN": "t", "GRANTED_SCOPES": "x",
             "LLM_ENDPOINT": "http://127.0.0.1:9", "STATE_DIR": "/proc/no-such-dir/x"},
        timeout=60,
    )
    assert result.returncode == 78, result.stderr[-400:]
    assert "STATE_DIR" in result.stderr and "Traceback" not in result.stderr


def test_an_action_is_refused_by_the_gate_before_anything_costs_money(emission):
    """An unapproved tool call once paid for a model call first. The gates
    run first on the request path and answer 409, not 500."""
    shape, out = emission
    if not (out / "app" / "controls.py").exists():
        pytest.skip("nothing mutative in this shape")
    pipeline = (out / "app" / "pipeline.py").read_text()
    steps = pipeline.split("\nSTEPS = [", 1)[1].split("]", 1)[0]
    first = steps.lstrip()
    assert first.startswith("('approve-") or first.startswith("('critic-"), steps[:120]
    code = """
from app import pipeline
from app.controls import NeedsApproval
try:
    pipeline.run({"tool": "delete", "arguments": {}})
except NeedsApproval:
    print("ok")
"""
    result = run_in(out, code, env={"LLM_ENDPOINT": "http://127.0.0.1:9"})
    assert result.returncode == 0 and "ok" in result.stdout, result.stderr[-600:]


def test_the_unit_does_not_restart_a_refused_configuration(emission):
    shape, out = emission
    unit = out / "deploy" / "systemd" / "app.service"
    if not unit.exists():
        pytest.skip("no unit in this shape")
    text = unit.read_text()
    assert "RestartPreventExitStatus=78" in text
    assert "-m app.service" in text



def test_the_request_contract_is_this_builds_not_everyones(emission):
    """A key nothing on this build's request path reads is refused, not
    ignored: a caller once sent `documents` to a build that ingests at
    boot and got a confident answer from a different corpus."""
    shape, out = emission
    code = """
from app.shapes import CALLER_KEYS, envelope
from app.contract import RefusedInput
import sys
has_retrieval = __import__("pathlib").Path("app/components/retrieval.py").exists()
if has_retrieval:
    assert "documents" not in CALLER_KEYS, CALLER_KEYS
    try:
        envelope({"query": "q", "documents": [{"id": "x", "text": "t"}]})
        raise SystemExit("documents accepted on an ingest-at-boot build")
    except RefusedInput:
        pass
else:
    assert "documents" in CALLER_KEYS or "pages" in CALLER_KEYS, CALLER_KEYS
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"


def test_a_stopword_is_not_evidence(emission):
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    code = """
from app.components.retrieval import Retrieval
r = Retrieval()
r.index([{"id": "http", "text": "The HTTP 301 status means the resource moved permanently."},
         {"id": "office", "text": "The office closes at six on the last day."},
         {"id": "sku", "text": "The SKU-99312 costs the sum of forty dollars."}])
assert r.retrieve("How do I reset the payroll database?", 5) == [], "a stopword cited a document"
assert "appear in the corpus" in r.last_note, r.last_note
hits = r.retrieve("SKU-99312", 5)
assert hits and hits[0]["id"] == "sku" and hits[0]["score"] > 0, hits
# A one-document corpus must still answer the question it holds: every
# token is 'ubiquitous' there, and a hard cut once retrieved nothing.
one = Retrieval()
one.index([{"id": "rfc",
            "text": "HTTP status 301 Moved Permanently means the resource has a new URI."}])
assert one.retrieve("Which status code means moved permanently?", 5), one.last_note
# A homogeneous corpus where the domain word is in every document: the
# common-term query ranks (weakly) rather than returning nothing.
hr = Retrieval()
hr.index([{"id": f"hr-{i}", "text": f"policy number {i}: leave policy applies to staff"}
          for i in range(50)])
assert hr.retrieve("What is the policy?", 5), hr.last_note
assert "common" in hr.last_note, hr.last_note
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"


def test_one_bad_jsonl_line_loses_one_record_not_the_file(emission):
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    corpus = out / "corpus-jsonl"
    corpus.mkdir(exist_ok=True)
    (corpus / "export.jsonl").write_text(
        '{"id": "a", "text": "alpha alpha"}\n'
        '{"id": "b", "text": "beta"\n'
        '{"id": "c", "text": "gamma"}\n')
    code = """
from app import pipeline
n = pipeline.load_corpus("corpus-jsonl")
print(n, pipeline.LOADED["skipped"])
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"
    expected = "2 [{'file': 'export.jsonl', 'reason': '1 malformed"
    assert result.stdout.startswith(expected), result.stdout


def test_a_corpus_over_the_sized_ceiling_refuses_the_boot(emission):
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    corpus = out / "corpus-big"
    corpus.mkdir(exist_ok=True)
    (corpus / "big.txt").write_text("word " * 60_000)  # 300KB of text
    result = subprocess.run(
        [sys.executable, "-m", "app.service"], cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "PORT": "18997", "AUTH_TOKEN": "t", "GRANTED_SCOPES": "x",
             "LLM_ENDPOINT": "http://127.0.0.1:9", "CORPUS_DIR": str(corpus),
             "CORPUS_MAX_MB": "0.1"},
        timeout=60,
    )
    assert result.returncode == 78 and "CORPUS_MAX_MB" in result.stderr, result.stderr[-400:]
    assert "Traceback" not in result.stderr


def test_a_boundary_violation_is_one_line_and_exit_78(emission):
    shape, out = emission
    if not (out / "app" / "boundary.py").exists():
        pytest.skip("no boundary in this shape")
    result = subprocess.run(
        [sys.executable, "-m", "app.service"], cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "PORT": "18996", "AUTH_TOKEN": "t",
             "LLM_ENDPOINT": "https://exfil.example.com.local"}, timeout=60,
    )
    assert result.returncode == 78, result.stderr[-400:]
    assert "outside the boundary" in result.stderr and "Traceback" not in result.stderr
    metadata = run_in(out, "import app.boundary", env={"LLM_ENDPOINT": "http://169.254.169.254/"})
    assert metadata.returncode != 0, "link-local (the cloud metadata address) must be outside"


def test_readiness_degrades_on_a_stray_file_and_probes_on_first_poll(emission):
    """A .DS_Store beside the corpus must not take a healthy service out
    of rotation; and the first /ready must probe, never answer from a
    fresh cache."""
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    import json as jsonlib
    import socket
    import time
    import urllib.error
    import urllib.request

    corpus = out / "corpus-stray"
    corpus.mkdir(exist_ok=True)
    (corpus / "good.txt").write_text("alpha beta gamma")
    (corpus / ".DS_Store").write_bytes(b"\x00\x01")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.service"], cwd=out,
        env={"PATH": "/usr/bin", "PORT": str(port), "AUTH_TOKEN": "s3cret",
             "GRANTED_SCOPES": "x", "LLM_ENDPOINT": "http://127.0.0.1:9",
             "CORPUS_DIR": str(corpus)},
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
        try:
            urllib.request.urlopen(base + "/ready", timeout=5)
            raise AssertionError("the model is unreachable; the first poll must say so")
        except urllib.error.HTTPError as e:
            body = jsonlib.loads(e.read())
            assert e.code == 503
            problems = " ".join(body["problems"])
            assert "unreachable" in problems and "skipped" not in problems, body
    finally:
        proc.terminate()
        proc.wait(timeout=20)


def test_a_malformed_models_listing_is_a_finding_not_a_dropped_socket(emission):
    shape, out = emission
    if "NEEDS_MODEL = True" not in (out / "app" / "service.py").read_text():
        pytest.skip("this shape needs no model")
    import json as jsonlib
    import socket
    import threading
    import time
    import urllib.error
    import urllib.request
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Gateway(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'["stub"]'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    gateway = HTTPServer(("127.0.0.1", 0), Gateway)
    threading.Thread(target=gateway.serve_forever, daemon=True).start()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.service"], cwd=out,
        env={"PATH": "/usr/bin", "PORT": str(port), "AUTH_TOKEN": "s3cret",
             "GRANTED_SCOPES": "x", "LLM_ENDPOINT": f"http://127.0.0.1:{gateway.server_port}",
             "LLM_MODEL": "m"},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            if proc.poll() is not None:
                raise AssertionError(f"exited {proc.returncode}: {proc.stdout.read()[:600]}")
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        try:
            urllib.request.urlopen(base + "/ready", timeout=5)
        except urllib.error.HTTPError as e:
            assert e.code == 503 and "malformed" in " ".join(jsonlib.loads(e.read())["problems"])
        else:
            raise AssertionError("a gateway answering a list is not a ready model")
    finally:
        proc.terminate()
        proc.wait(timeout=20)
        gateway.shutdown()


def test_an_unresolvable_bind_is_exit_78(emission):
    shape, out = emission
    result = subprocess.run(
        [sys.executable, "-m", "app.service"], cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "PORT": "18995", "AUTH_TOKEN": "t", "GRANTED_SCOPES": "x",
             "LLM_ENDPOINT": "http://127.0.0.1:9", "BIND": "not-a-host.invalid"}, timeout=60,
    )
    assert result.returncode == 78 and "BIND" in result.stderr, result.stderr[-300:]



def test_a_scalar_corpus_record_is_skipped_not_a_traceback(emission):
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    corpus = out / "corpus-scalar"
    corpus.mkdir(exist_ok=True)
    (corpus / "export.json").write_text('[{"id": "a", "text": "alpha"}, null, 123, "bare"]')
    code = """
from app import pipeline
n = pipeline.load_corpus("corpus-scalar")
names = sorted(s["file"] for s in pipeline.LOADED["skipped"])
print(n, names)
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"
    expected = "1 ['record NoneType', 'record int', 'record str']"
    assert result.stdout.startswith(expected), result.stdout


def test_compaction_keeps_a_key_another_process_reserved(emission):
    """The operator's compaction re-reads the file under the directory
    lock: a key the running service reserved after the CLI started must
    survive, or a retry of that action happens twice."""
    shape, out = emission
    if not (out / "app" / "ledger.py").exists():
        pytest.skip("nothing outward in this shape")
    state = out / "state-compact"
    state.mkdir(exist_ok=True)
    code = """
import json, time
from app.ledger import LEDGER, Ledger
old = LEDGER.key_for({"tool": "old"})
LEDGER.reserve(old, "d"); LEDGER.complete(old, "done")
# age it past the retention, on disk and in memory
for r in (LEDGER._keys[old],):
    r["completed_at"] = time.time() - 10 * 86400
LEDGER._write("idempotency.jsonl", LEDGER._keys[old])
# another process reserves a key the CLI's snapshot never saw
other = Ledger(str(LEDGER.root))
live = other.key_for({"tool": "live"})
assert other.reserve(live, "d") is None
dropped = LEDGER.compact(retention_seconds=86400)
fresh = Ledger(str(LEDGER.root))
assert live in fresh._keys, "compaction dropped a key reserved by another process"
assert old not in fresh._keys and dropped == 1, (dropped, list(fresh._keys))
print("ok")
"""
    result = run_in(out, code, env={"STATE_DIR": str(state)})
    assert result.returncode == 0, f"{shape}: {result.stderr[-800:]}"


def test_every_eval_entry_point_imports_the_boundary(emission):
    shape, out = emission
    if not (out / "app" / "boundary.py").exists():
        pytest.skip("no boundary in this shape")
    for name in ("harness.py", "calibrate.py"):
        script = out / "evals" / name
        if not script.exists():
            continue
        assert "import app.boundary" in script.read_text(), f"{shape}: {name} skips the boundary"
        result = subprocess.run(
            [sys.executable, str(script)], cwd=out, capture_output=True, text=True,
            env={"PATH": "/usr/bin", "JUDGE_ENDPOINT": "https://exfil.example.com",
                 "LLM_ENDPOINT": "http://127.0.0.1:9"}, timeout=60,
        )
        assert result.returncode == 78, f"{shape}: {name}: {result.stderr[-300:]}"
        assert "outside the boundary" in result.stderr and "Traceback" not in result.stderr


def test_a_goal_is_a_question(emission):
    shape, out = emission
    code = """
from app.shapes import CALLER_KEYS, envelope
if "goal" in CALLER_KEYS:
    assert envelope({"goal": "find the total"})["query"] == "find the total"
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-400:]}"


def test_a_denied_tool_call_leaves_an_audit_record(emission):
    shape, out = emission
    integration = out / "app" / "components" / "integration.py"
    if not integration.exists() or "governed-tools" not in integration.read_text():
        pytest.skip("no governed tool boundary in this shape")
    state = out / "state-denied"
    state.mkdir(exist_ok=True)
    code = """
import json
from pathlib import Path
from app.components.integration import Integration, Tool, ScopeDenied, UnregisteredTool
i = Integration()
i.register(Tool(name="refund", run=lambda **a: "done", required_scope="finance",
                input_schema={"amount": "int"}))
for call, error in ((("nope", {}), UnregisteredTool), (("refund", {"amount": 1}), ScopeDenied)):
    try:
        i.call(call[0], call[1], subject="alice", granted_scopes=set(), request_id="r1")
    except error:
        pass
records = [json.loads(l) for l in Path("state-denied/audit.jsonl").read_text().splitlines()]
denied = [r for r in records if r["phase"] == "denied"]
assert len(denied) == 2 and denied[1]["request_id"] == "r1", records
print("ok")
"""
    result = run_in(out, code, env={"STATE_DIR": str(state)})
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"



def test_a_truncated_query_is_never_a_silent_miss(emission):
    shape, out = emission
    if not (out / "app" / "components" / "retrieval.py").exists():
        pytest.skip("no retrieval layer in this shape")
    code = """
from app.components.retrieval import Retrieval, MAX_QUERY_TOKENS
r = Retrieval()
r.index([{"id": "sku", "text": "SKU-88317 ships from the Leeds depot"},
         {"id": "other", "text": "quarterly figures and the office calendar"}])
query = " ".join(f"filler{i}" for i in range(MAX_QUERY_TOKENS + 90)) + " SKU-88317"
assert r.retrieve(query, 5) == []
assert "truncated" in r.last_note, r.last_note
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-500:]}"


def test_two_processes_cannot_both_reserve_one_key(emission):
    """A debug run beside the unit, or a failover before the old instance
    is dead: two ledgers on one STATE_DIR must agree on who owns a key."""
    shape, out = emission
    if not (out / "app" / "ledger.py").exists():
        pytest.skip("nothing outward in this shape")
    state = out / "state-race"
    state.mkdir(exist_ok=True)
    code = """
import threading
from app.ledger import Ledger, KeyUnresolved
a, b = Ledger("state-race"), Ledger("state-race")
key = a.key_for({"tool": "pay", "arguments": {"amount": 5}})
barrier = threading.Barrier(2)
outcomes = []
def attempt(ledger):
    barrier.wait()
    try:
        outcomes.append(("owned", ledger.reserve(key, "d")))
    except KeyUnresolved:
        outcomes.append(("refused", None))
threads = [threading.Thread(target=attempt, args=(led,)) for led in (a, b)]
[t.start() for t in threads]; [t.join() for t in threads]
kinds = sorted(k for k, _ in outcomes)
assert kinds == ["owned", "refused"], outcomes
lines = [l for l in open("state-race/idempotency.jsonl").read().splitlines() if l.strip()]
assert len(lines) == 1, lines
print("ok")
"""
    result = run_in(out, code)
    assert result.returncode == 0, f"{shape}: {result.stderr[-600:]}"
