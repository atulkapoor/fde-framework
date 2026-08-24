"""Memory and retrieval, as emitted.

Both turned out to be the cascade again. Retrieval runs an exact lexical tier
and a semantic one and fuses them, because each fails where the other works.
Memory keeps cheaply, promotes deliberately, and has to know that a fact can
stop being true.
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
    output_shape="freeform", input_format="documents", query_pattern="lookup",
    corpus_size=200_000, data_residency="cannot_leave", hosting="air-gapped",
    latency_budget_ms=800, external_systems=3, recall_span="across_sessions",
    operates_after_handover="platform_team", cheap_path_coverage=0.99,
    confidence_calibrated=True,
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


@pytest.fixture(scope="module")
def built(reg, tmp_path_factory):
    out = tmp_path_factory.mktemp("mem")
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in CASE.items()])
    emit(architect(p, reg), out)
    return out


def run_in(project, code):
    return subprocess.run(
        [sys.executable, "-c", code], cwd=project, capture_output=True, text=True
    )


# --- retrieval: each tier fails where the other works --------------------


def test_an_identifier_is_found_by_the_lexical_tier(built):
    """Vector search fumbles part numbers and account references. Lexical
    matching does not, which is why both are run."""
    result = run_in(built, """
from app.components.retrieval import Retrieval
r = Retrieval()
r.index([{"id": "1", "text": "Invoice for part SKU-99312 shipped Tuesday"},
         {"id": "2", "text": "A general note about logistics and delivery"}])
assert r.retrieve("SKU-99312")[0]["id"] == "1"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_results_are_fused_on_rank_not_on_score(built):
    """Scores from two retrievers are not on the same scale, and averaging them
    is the thing that quietly breaks in production."""
    result = run_in(built, """
from app.components.retrieval import fuse
fused = fuse({"lexical": ["a", "b", "c"], "semantic": ["c", "a", "d"]})
assert fused[0] in ("a", "c"), "something in both lists should lead"
assert set(fused) == {"a", "b", "c", "d"}
print(fused)
""")
    assert result.returncode == 0, result.stderr


def test_a_document_both_tiers_agree_on_outranks_one_only_either_found(built):
    result = run_in(built, """
from app.components.retrieval import fuse
fused = fuse({"lexical": ["shared", "lexonly"], "semantic": ["shared", "semonly"]})
assert fused[0] == "shared"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_fusion_needs_no_scores_at_all(built):
    """Rank-only is the point: it works across retrievers that share nothing."""
    result = run_in(built, """
from app.components.retrieval import fuse
assert fuse({"only": ["x", "y"]}) == ["x", "y"]
print("ok")
""")
    assert result.returncode == 0, result.stderr


# --- memory: tiers, and knowing a fact stopped being true ----------------


def test_working_state_is_not_promoted_by_default(built):
    """A mistake in working state should disappear with the session. The same
    mistake promoted becomes permanent and is recalled confidently."""
    result = run_in(built, """
from app.components.memory import Memory
m = Memory()
m.note("session-1", "user seems annoyed")
assert m.recall_long_term() == []
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_promotion_is_explicit(built):
    result = run_in(built, """
from app.components.memory import Memory
m = Memory()
m.note("session-1", "prefers metric units")
m.promote("session-1", "prefers metric units", because="stated three times")
assert any("metric" in f["value"] for f in m.recall_long_term())
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_a_superseded_fact_stops_being_recalled_but_is_not_erased(built):
    """The named open problem: someone changes employer, and a memory that
    only appends keeps asserting the old one with full confidence."""
    result = run_in(built, """
from app.components.memory import Memory
m = Memory()
m.remember("employer", "Northwind", because="stated in March")
m.remember("employer", "Contoso", because="stated in August")
current = {f["key"]: f["value"] for f in m.recall_long_term()}
assert current["employer"] == "Contoso"
assert len(m.history("employer")) == 2, "what was true is kept, just not returned"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_contradictory_facts_are_not_both_returned(built):
    """Attention dilution: retrieved context holding two answers produces an
    incoherent one. Consolidation is about coherence before it is about cost."""
    result = run_in(built, """
from app.components.memory import Memory
m = Memory()
m.remember("employer", "Northwind", because="March")
m.remember("employer", "Contoso", because="August")
values = [f["value"] for f in m.recall_long_term() if f["key"] == "employer"]
assert len(values) == 1
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_unused_memories_decay(built):
    """A memory that only grows is a slower context window."""
    result = run_in(built, """
from app.components.memory import Memory
m = Memory()
m.remember("trivia", "liked the blue theme", because="once", now=0)
m.sweep(now=10_000_000)          # comfortably past the decay window
assert not any(f["key"] == "trivia" for f in m.recall_long_term())
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_re_access_keeps_a_memory_alive(built):
    result = run_in(built, """
from app.components.memory import Memory
m = Memory()
m.remember("trivia", "liked the blue theme", because="once", now=0)
for _ in range(5):
    m.recall_long_term()
m.sweep(now=10_000_000)
assert any(f["key"] == "trivia" for f in m.recall_long_term()), "used memories survive"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_memory_of_regulated_data_stays_inside_the_boundary(built):
    result = run_in(built, """
from app.boundary import PLACEMENT
assert PLACEMENT.get("memory") == "in_boundary"
print("ok")
""")
    assert result.returncode == 0, result.stderr
