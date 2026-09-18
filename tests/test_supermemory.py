"""The supermemory realization of the episodic store.

An engine-backed memory is a second stateful system holding client data,
so it is offered only where the profile already runs it, refuses the
hosted endpoint behind a boundary, and speaks the engine's documented API
(two POSTs) with no dependency -- all of which is pinned here.
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
from fde.realization import realization_for
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"

CASE = dict(
    output_shape="freeform", input_format="text", corpus_size=40_000,
    data_residency="cannot_leave", hosting="on-prem", external_systems=2,
    human_waiting="no", query_pattern="lookup", recall_span="across_sessions",
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


@pytest.fixture(scope="module")
def built(reg, tmp_path_factory):
    out = tmp_path_factory.mktemp("supermemory")
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in CASE.items()])
    emit(architect(p, reg, already_running={"supermemory"}), out, registry=reg)
    return out


def run_in(project: Path, code: str, env: dict | None = None):
    return subprocess.run(
        [sys.executable, "-c", code], cwd=project, capture_output=True,
        text=True, env={"PATH": "/usr/bin", **(env or {})},
    )


def test_the_engine_is_offered_only_where_it_already_runs(reg):
    plain = realization_for("episodic-store", "memory", reg, "on-prem")
    assert plain.stack == "plain-python"
    reused = realization_for("episodic-store", "memory", reg, "on-prem",
                             already_running={"supermemory"})
    assert reused.stack == "supermemory"


def test_the_engine_is_not_offered_air_gapped(reg):
    # The local binary fetches its embedding model on first boot; until
    # that staging is verified inside an air gap, the registry says no.
    assert "air-gapped" not in reg.stacks["supermemory"].topologies
    assert reg.stacks["supermemory"].licence == "MIT"


def test_the_emitted_memory_speaks_the_documented_api(built):
    code = """
from app.components.memory import Memory
calls = []
def fake(method, path, body):
    calls.append((method, path, body))
    if path == "/v3/search":
        return {"results": [{"content": "employer: Acme", "score": 0.9,
                             "metadata": {"key": "employer"}}]}
    return {"id": "doc_1"}
m = Memory(container="user_1", transport=fake)
assert m.stack == "supermemory"
assert m.remember("employer", "Acme", because="said so") == "doc_1"
method, path, body = calls[0]
assert (method, path) == ("POST", "/v3/documents"), calls
assert body["containerTag"] == "user_1" and body["content"] == "employer: Acme"
assert body["metadata"]["because"] == "said so"
got = m.recall("where do they work")
assert calls[1][1] == "/v3/search" and calls[1][2]["searchMode"] == "memories"
assert got[0]["content"] == "employer: Acme"
assert m.history("employer")[0]["metadata"]["key"] == "employer"
assert m.sweep() == []
print("ok")
"""
    result = run_in(built, code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_the_hosted_endpoint_is_refused_behind_a_boundary(built):
    assert (built / "app" / "boundary.py").exists()
    code = ("from app.components.memory import Memory\n"
            "Memory(transport=lambda *a: {})\n")
    result = run_in(built, code, env={"SUPERMEMORY_ENDPOINT": "https://api.supermemory.ai"})
    assert result.returncode != 0
    # Two fences, either may fire first: the boundary refuses the URL at
    # import, and the module refuses the hosted host on construction.
    assert ("hosted memory service is refused" in result.stderr
            or "outside the boundary" in result.stderr), result.stderr
    # The local binary is fine, and construction touches no network.
    ok = run_in(built, code, env={"SUPERMEMORY_ENDPOINT": "http://localhost:6767"})
    assert ok.returncode == 0, ok.stderr


def test_the_emitted_memory_is_lint_clean(built):
    pytest.importorskip("ruff")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--isolated",
         "--select", "F,E,W,I,B,UP", "--line-length", "100",
         str(built / "app" / "components" / "memory.py")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout


def test_the_engines_variables_are_documented(built):
    env = (built / "deploy" / "env.example").read_text()
    for var in ("SUPERMEMORY_ENDPOINT", "SUPERMEMORY_API_KEY", "SUPERMEMORY_TIMEOUT"):
        assert var in env, f"{var} is read by the emitted memory but undocumented"
