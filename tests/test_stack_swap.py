"""Swapping the stack changes the code and not the architecture.

That seam is why patterns and stacks are separate registries at all. Patterns
are stable for years; the libraries implementing them churn in months. If a swap
moved the design, the separation would be a fiction.
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
    output_shape="freeform", input_format="documents", query_pattern="comparative",
    corpus_size=200_000, data_residency="may_leave", hosting="customer-vpc",
    latency_budget_ms=800, external_systems=3, recall_span="within_session",
    operates_after_handover="platform_team", human_waiting="yes",
    cheap_path_coverage=0.99,
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def build(reg, out, already_running=None):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in CASE.items()])
    architecture = architect(p, reg, already_running=already_running)
    emit(architecture, out)
    return architecture


def test_reuse_changes_the_stack(reg, tmp_path):
    """A client already running Postgres should not be handed a second store
    to operate."""
    plain = build(reg, tmp_path / "plain")
    reused = build(reg, tmp_path / "reused", already_running={"pgvector"})
    assert plain.realizations["retrieval"].stack == "plain-python"
    assert reused.realizations["retrieval"].stack == "pgvector"


def test_the_emitted_code_differs(reg, tmp_path):
    plain = tmp_path / "plain"
    reused = tmp_path / "reused"
    build(reg, plain)
    build(reg, reused, already_running={"pgvector"})
    a = (plain / "app" / "components" / "retrieval.py").read_text()
    b = (reused / "app" / "components" / "retrieval.py").read_text()
    assert a != b
    assert "vector(" in b and "vector(" not in a


def test_the_architecture_does_not(reg, tmp_path):
    """The decisive assertion. Same components, same approaches, same
    placement -- a different library underneath."""
    plain = build(reg, tmp_path / "plain")
    reused = build(reg, tmp_path / "reused", already_running={"pgvector"})
    assert plain.fingerprint() == reused.fingerprint()
    assert plain.graph == reused.graph


def test_both_satisfy_the_same_interface(reg, tmp_path):
    plain = build(reg, tmp_path / "plain")
    reused = build(reg, tmp_path / "reused", already_running={"pgvector"})
    assert (
        plain.realizations["retrieval"].provides
        == reused.realizations["retrieval"].provides
    )


def test_both_projects_import(reg, tmp_path):
    for name, running in (("plain", None), ("reused", {"pgvector"})):
        out = tmp_path / name
        build(reg, out, already_running=running)
        result = subprocess.run(
            [sys.executable, "-c", "import app.pipeline"],
            cwd=out, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{name}: {result.stderr}"


def test_the_in_process_implementation_actually_retrieves(reg, tmp_path):
    out = tmp_path / "plain"
    build(reg, out)
    result = subprocess.run([sys.executable, "-c", """
from app.components.retrieval import Retrieval
r = Retrieval()
r.index([{"id": "1", "text": "invoices and billing"},
         {"id": "2", "text": "shipping and logistics"}])
assert r.retrieve("billing")[0]["id"] == "1"
print("ok")
"""], cwd=out, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_the_database_implementation_emits_usable_schema(reg, tmp_path):
    """It cannot be run without a database, so what is asserted is that it
    produces the statements somebody would run."""
    out = tmp_path / "reused"
    build(reg, out, already_running={"pgvector"})
    result = subprocess.run([sys.executable, "-c", """
from app.components.retrieval import Retrieval
r = Retrieval(dimensions=768)
assert "CREATE EXTENSION IF NOT EXISTS vector" in r.schema()
assert "ivfflat" in r.index_statement(rows=10_000)
print("ok")
"""], cwd=out, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
