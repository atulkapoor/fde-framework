"""Emitted components that actually run.

A scaffold states a contract. A realization implements it. Where the framework
has a reference implementation it should emit working code, and where it does
not it should say so rather than emit something that looks finished.

These tests run the emitted modules.
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

CASE = dict(
    output_shape="structured", input_format="documents", query_pattern="lookup",
    corpus_size=200_000, labelled_count=8_000, data_residency="cannot_leave",
    hosting="air-gapped", latency_budget_ms=800, external_systems=3,
    recall_span="within_session", operates_after_handover="platform_team",
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


@pytest.fixture(scope="module")
def built(reg, tmp_path_factory):
    out = tmp_path_factory.mktemp("built")
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in CASE.items()])
    emit(architect(p, reg), out)
    return out


def run_in(project: Path, code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code], cwd=project, capture_output=True, text=True
    )


# --- implemented, not scaffolded -----------------------------------------


def test_a_component_with_a_reference_implementation_is_not_a_stub(built):
    body = (built / "app" / "components" / "evaluation.py").read_text()
    assert "NotImplementedError" not in body


def test_the_emitted_scorer_scores(built):
    result = run_in(built, """
from app.components.evaluation import Evaluation
scored = Evaluation().run({
    "expected": [{"id": "a", "fields": {"total": "100", "date": "2026-01-01"}}],
    "actual":   [{"id": "a", "fields": {"total": "100", "date": "2026-01-02"}}],
})
assert scored["per_field"]["total"]["correct"] == 1
assert scored["per_field"]["date"]["correct"] == 0
print("ok")
""")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_the_scorer_reports_a_breakdown_not_one_number(built):
    """Eighty-eight percent says how often you fail. The shape of the twelve
    says what to build next."""
    result = run_in(built, """
from app.components.evaluation import Evaluation
scored = Evaluation().run({
    "expected": [{"id": "a", "fields": {"total": "1,000", "name": "X"}}],
    "actual":   [{"id": "a", "fields": {"total": "1000", "name": "Y"}}],
})
assert set(scored["per_field"]) == {"total", "name"}
assert scored["errors"], "failures must be classified, not just counted"
print(sorted({e["kind"] for e in scored["errors"]}))
""")
    assert result.returncode == 0, result.stderr


def test_unverified_records_are_scored_without_labels(built):
    """The 192,000 rows that cannot train a model can still be mined. Ignoring
    them is the more expensive mistake."""
    result = run_in(built, """
from app.components.evaluation import Evaluation
queue = Evaluation().mine([
    {"id": "a", "fields": {"total": "100", "date": "2026-01-01"}},
    {"id": "b", "fields": {"total": "", "date": "not-a-date"}},
])
assert queue[0]["id"] == "b", "the least self-consistent record is worth verifying first"
print("ok")
""")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


# --- the gate is real ----------------------------------------------------


def test_an_irreversible_action_cannot_proceed_without_approval(built):
    result = run_in(built, """
from app.components.governance import Governance
g = Governance()
try:
    g.run({"action": "send_email", "reversible": False, "payload": {"to": "x"}})
except PermissionError as e:
    print("refused:", e)
else:
    raise AssertionError("an irreversible action ran without approval")
""")
    assert result.returncode == 0, result.stderr
    assert "refused" in result.stdout


def test_the_same_action_twice_happens_once(built):
    """Structural impossibility beats testing for a double-charge."""
    result = run_in(built, """
from app.components.governance import Governance
g = Governance()
action = {"action": "update_record", "reversible": True, "payload": {"id": 7}}
first = g.run(action)
second = g.run(action)
assert second["duplicate"] is True, "a repeated action must not fire twice"
assert first["key"] == second["key"]
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_an_irreversible_action_stays_gated_however_accurate_it_has_been(built):
    """Autonomy is earned per action type, and never for actions that cannot
    be taken back."""
    result = run_in(built, """
from app.components.governance import Governance
g = Governance()
for _ in range(500):
    g.record_approval("send_email", edited=False)
assert not g.may_run_unattended("send_email"), "irreversible actions never graduate"
assert g.may_run_unattended("update_record") in (True, False)
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_autonomy_is_earned_from_measured_approvals(built):
    result = run_in(built, """
from app.components.governance import Governance
g = Governance()
assert not g.may_run_unattended("update_record"), "nothing is autonomous on day one"
for _ in range(200):
    g.record_approval("update_record", edited=False)
assert g.may_run_unattended("update_record"), "a measured record should earn it"
print("ok")
""")
    assert result.returncode == 0, result.stderr


# --- honesty about what is not implemented -------------------------------


def test_a_component_with_no_reference_implementation_says_so(built):
    """Better an honest stub than something that looks finished."""
    scaffolds = [
        p.name for p in (built / "app" / "components").glob("*.py")
        if "yours to write" in p.read_text()
    ]
    for name in scaffolds:
        assert "NotImplementedError" in (built / "app" / "components" / name).read_text()


def test_the_project_still_imports_with_scaffolds_present(built):
    assert run_in(built, "import app.pipeline").returncode == 0


# --- the tool boundary ---------------------------------------------------


def test_an_unregistered_tool_cannot_be_called(built):
    """The point of one entry is that nothing else has a way out."""
    result = run_in(built, """
from app.components.integration import Integration, UnregisteredTool
try:
    Integration().call("shell.exec", {}, subject="a", granted_scopes={"anything"})
except UnregisteredTool as e:
    print("refused:", e)
else:
    raise AssertionError("an unregistered tool ran")
""")
    assert result.returncode == 0, result.stderr
    assert "refused" in result.stdout


def test_authority_is_checked_against_the_caller_not_the_tools_own_claim(built):
    """A declaration is the tool describing itself. It is never permission."""
    result = run_in(built, """
from app.components.integration import Integration, ScopeDenied, Tool
b = Integration()
b.register(Tool(name="post", run=lambda **k: "done", required_scope="write:ledger",
                read_only=True, destructive=False))
try:
    b.call("post", {}, subject="r.iyer", granted_scopes={"read:ledger"})
except ScopeDenied as e:
    print("denied:", e)
else:
    raise AssertionError("a read-only claim granted a write it did not hold")
""")
    assert result.returncode == 0, result.stderr
    assert "denied" in result.stdout


def test_a_tool_is_assumed_destructive_unless_it_says_otherwise(built):
    """Guessing wrong this way costs a confirmation. The other way costs data."""
    result = run_in(built, """
from app.components.integration import Tool
assert Tool(name="x", run=lambda: None, required_scope="s").destructive is True
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_reversibility_is_tracked_apart_from_destructiveness(built):
    """Trash is destructive and reversible; permanent deletion is both. The
    distinction decides whether a critic is needed."""
    result = run_in(built, """
from app.components.integration import Integration, Tool
b = Integration()
b.register(Tool("trash", lambda **k: 1, "s", destructive=True, reversible=True))
b.register(Tool("purge", lambda **k: 1, "s", destructive=True, reversible=False))
assert b.irreversible_tools() == ["purge"]
assert set(b.mutative_tools()) == {"trash", "purge"}
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_the_audit_names_the_human_as_subject(built):
    """A record saying an agent issued a refund has lost the chain."""
    result = run_in(built, """
from app.components.integration import Integration, Tool
b = Integration()
b.register(Tool("post", lambda **k: "ok", "write", destructive=True))
b.call("post", {}, subject="r.iyer", granted_scopes={"write"}, actor="refund-agent")
assert b.audit[0]["subject"] == "r.iyer"
assert b.audit[0]["actor"] == "refund-agent"
assert [e["phase"] for e in b.audit] == ["intent", "outcome"]
print("ok")
""")
    assert result.returncode == 0, result.stderr


# --- tracing -------------------------------------------------------------


def test_the_tracer_pins_the_convention_version_it_was_written_against(built):
    """These names are pre-stable. A rename should arrive as a diff, not a
    mystery."""
    result = run_in(built, """
from app.components.observability import Observability
assert Observability.convention_version
print(Observability.convention_version)
""")
    assert result.returncode == 0, result.stderr


def test_the_tracer_records_a_trajectory_not_isolated_events(built):
    result = run_in(built, """
from app.components.observability import Observability
t = Observability(tenant="acme")
with t.span("outer", "invoke_workflow"):
    with t.span("inner", "execute_tool"):
        pass
path = t.trajectory()
assert len(path) == 2
assert any(p["parent"] for p in path), "a loop is debugged from the path, not the nodes"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_cost_is_attributed_per_tenant(built):
    """Retrofitting this means touching every call site, so it is architectural."""
    result = run_in(built, """
from app.components.observability import Observability
t = Observability(tenant="acme")
with t.span("call", "chat") as s:
    t.record_model_call(s, model="m", input_tokens=100, output_tokens=20)
assert t.cost_by_tenant()["acme"]["input_tokens"] == 100
print("ok")
""")
    assert result.returncode == 0, result.stderr
