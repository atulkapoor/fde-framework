"""The last four components, emitted as working code.

Each carries the thing that is usually got wrong. Perception measures what it
lost rather than losing it quietly. Deterministic mapping fails loudly instead
of producing a well-formed wrong answer. Reasoning is bounded. Serving does the
memory arithmetic before anyone deploys and finds out.
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
    latency_budget_ms=800, external_systems=3, recall_span="within_session",
    operates_after_handover="platform_team", cheap_path_coverage=0.99,
    human_waiting="yes",
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


@pytest.fixture(scope="module")
def built(reg, tmp_path_factory):
    out = tmp_path_factory.mktemp("rest")
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in CASE.items()])
    emit(architect(p, reg), out)
    return out


def run_in(project, code):
    return subprocess.run(
        [sys.executable, "-c", code], cwd=project, capture_output=True, text=True
    )


# --- perception: say what was lost ---------------------------------------


def test_extraction_reports_what_it_could_not_keep(built):
    """This caps everything downstream. A parser that flattens a table quietly
    sets the ceiling and nobody finds out until the answers are wrong."""
    result = run_in(built, """
from app.components.perception import Perception
out = Perception().run({"documents": [
    {"id": "1", "text": "Total  100 | Tax  20 | Net  80\\nSecond row  1 | 2 | 3"},
]})
assert out["records"][0]["losses"], "a flattened table must be reported"
print(out["records"][0]["losses"])
""")
    assert result.returncode == 0, result.stderr


def test_clean_prose_reports_no_losses(built):
    result = run_in(built, """
from app.components.perception import Perception
out = Perception().run({"documents": [{"id": "1", "text": "A plain sentence."}]})
assert out["records"][0]["losses"] == []
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_the_ceiling_is_reported_for_the_batch(built):
    """One number an FDE can quote before promising anything downstream."""
    result = run_in(built, """
from app.components.perception import Perception
out = Perception().run({"documents": [
    {"id": "1", "text": "clean sentence"},
    {"id": "2", "text": "a | b | c\\nd | e | f"},
]})
assert 0 < out["clean_share"] < 1
print(out["clean_share"])
""")
    assert result.returncode == 0, result.stderr


# --- serving: the arithmetic before the deployment -----------------------


def test_a_model_that_will_not_fit_is_said_so_before_deployment(built):
    result = run_in(built, """
from app.components.serving import Serving
plan = Serving().plan(params_b=70, precision="bf16", vram_gb=80)
assert not plan["fits"]
assert plan["shortfall_gb"] > 0
print(plan["advice"][0])
""")
    assert result.returncode == 0, result.stderr


def test_the_levers_are_offered_cheapest_first(built):
    """Quantisation, then adaptation, then distillation. Each costs more effort
    and more quality than the one before, so stop at the first that fits."""
    result = run_in(built, """
from app.components.serving import Serving
advice = Serving().plan(params_b=70, precision="bf16", vram_gb=80)["advice"]
assert "quantis" in advice[0].lower()
print(advice)
""")
    assert result.returncode == 0, result.stderr


def test_prefix_caching_is_on_by_default(built):
    """The single highest-value flag for most workloads, and free."""
    result = run_in(built, """
from app.components.serving import Serving
assert Serving().config(concurrent=16)["enable_prefix_caching"] is True
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_concurrency_defaults_differ_for_waiting_and_batch(built):
    """Somebody waiting wants headroom; a batch job wants throughput."""
    result = run_in(built, """
from app.components.serving import Serving
s = Serving()
assert s.config(human_waiting=True)["max_num_seqs"] < s.config(human_waiting=False)["max_num_seqs"]
print(s.config(human_waiting=True)["max_num_seqs"], s.config(human_waiting=False)["max_num_seqs"])
""")
    assert result.returncode == 0, result.stderr


def test_the_kv_cache_is_counted_not_ignored(built):
    """Naive sizing counts weights and forgets the cache, then runs out of
    memory under the load it was sized for."""
    result = run_in(built, """
from app.components.serving import Serving
plan = Serving().plan(params_b=8, precision="bf16", vram_gb=24,
                      max_num_seqs=64, max_model_len=8192)
assert plan["kv_cache_gb"] > 0
assert plan["weights_gb"] + plan["kv_cache_gb"] <= plan["required_gb"] + 0.01
print(plan["weights_gb"], plan["kv_cache_gb"])
""")
    assert result.returncode == 0, result.stderr


# --- reasoning: bounded, and it says why it stopped ----------------------


def test_the_loop_is_bounded(built):
    """A loop with no cap is an outage waiting for a slow afternoon."""
    result = run_in(built, """
from app.components.reasoning import Reasoning
r = Reasoning(max_steps=3)
out = r.run({"goal": "never satisfiable", "act": lambda s: {"done": False}})
assert out["steps"] == 3
assert out["stopped_because"] == "step_cap"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_it_says_why_it_stopped(built):
    """The two predicates are where a system decides anything, so a run that
    cannot say which one ended it cannot be debugged."""
    result = run_in(built, """
from app.components.reasoning import Reasoning
out = Reasoning().run({"goal": "g", "act": lambda s: {"done": True, "answer": 42}})
assert out["stopped_because"] == "goal_achieved"
assert out["answer"] == 42
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_a_budget_stops_it_even_below_the_step_cap(built):
    result = run_in(built, """
from app.components.reasoning import Reasoning
r = Reasoning(max_steps=100, max_cost=2)
out = r.run({"goal": "g", "act": lambda s: {"done": False, "cost": 1}})
assert out["stopped_because"] == "budget"
print(out["steps"])
""")
    assert result.returncode == 0, result.stderr


def test_answering_directly_costs_no_steps(built):
    """The first predicate: can this be answered without acting at all."""
    result = run_in(built, """
from app.components.reasoning import Reasoning
out = Reasoning().run({"goal": "g", "known": {"g": "already known"}})
assert out["steps"] == 0
assert out["stopped_because"] == "answered_directly"
print("ok")
""")
    assert result.returncode == 0, result.stderr
