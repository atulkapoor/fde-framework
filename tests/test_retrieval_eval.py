"""The retrieval layer, measured alone.

The embedding and index choices set a ceiling on everything downstream --
no reranking, prompting or model upgrade recovers a document that was never
retrieved. The emitted eval is what turns that ceiling from a suspicion
into a number, which is why it ships only where a retrieval layer exists
to measure, refuses an empty case set, and gates CI.
"""

import json
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

# Freeform output is what puts a retrieval component in scope at all --
# retrieval is required_when output_shape is freeform or ranking.
BASE = dict(
    output_shape="freeform", input_format="documents", query_pattern="lookup",
    corpus_size=200_000, latency_budget_ms=800, external_systems=2,
    recall_span="within_session", operates_after_handover="platform_team",
    cheap_path_coverage=0.99,
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def build(reg, out, values=None):
    p = Profile()
    p.ingest([
        Fact(k, v, Provenance.ARTIFACT)
        for k, v in (values if values is not None else BASE).items()
    ])
    emit(architect(p, reg), out)
    return out


@pytest.fixture(scope="module")
def project(reg, tmp_path_factory):
    return build(reg, tmp_path_factory.mktemp("retrieval_eval"))


def run_eval(project, *args):
    return subprocess.run(
        [sys.executable, "evals/retrieval.py", *args],
        cwd=project, capture_output=True, text=True,
    )


# --- where it ships -------------------------------------------------------


def test_a_retrieval_system_ships_the_retrieval_eval(project):
    assert (project / "evals" / "retrieval.py").exists()
    # Empty rather than absent: a gap somebody can see.
    assert (project / "evals" / "retrieval_cases.jsonl").exists()


def test_a_system_without_retrieval_does_not(reg, tmp_path):
    """An instruction to measure a layer that does not exist helps nobody."""
    out = build(reg, tmp_path, values=dict(
        output_shape="structured", input_format="documents",
        external_systems=1, latency_budget_ms=800,
    ))
    assert not (out / "evals" / "retrieval.py").exists()


def test_ci_gates_on_the_retrieval_layer(project):
    ci = (project / ".github" / "workflows" / "ci.yml").read_text()
    assert "evals/retrieval.py" in ci


def test_the_diagnosis_walk_points_at_the_measurement(project):
    """'The right answer is not in the evidence' should end at a number,
    not a feeling."""
    body = (project / "ops" / "diagnosis.md").read_text()
    assert "evals/retrieval.py" in body


# --- how it grades --------------------------------------------------------


def test_an_empty_case_file_is_a_failing_grade(project):
    """An empty exam graded green is how CI stays green on a system nobody
    measured."""
    result = run_eval(project)
    assert result.returncode == 1
    assert "nothing was measured" in result.stderr


def test_recall_is_measured_against_the_wired_retriever(reg, tmp_path_factory):
    out = build(reg, tmp_path_factory.mktemp("wired"))
    (out / "evals" / "retrieval_cases.jsonl").write_text(
        json.dumps({"id": "c1", "query": "alpha", "relevant": ["doc-1", "doc-9"]})
        + "\n"
    )
    (out / "app" / "components" / "retrieval.py").write_text(
        "def run(query, top_k=8):\n"
        "    return [{'id': 'doc-1'}, {'id': 'doc-2'}]\n"
    )
    result = run_eval(out)
    assert "recall@10" in result.stdout
    assert "50.0%" in result.stdout
    # Half the relevant ids surfaced: above zero, so without a stated
    # threshold this passes -- and the miss is named on stderr.
    assert result.returncode == 0
    assert "doc-9" in result.stderr


def test_recall_below_the_threshold_fails_and_says_where_to_look(
    reg, tmp_path_factory
):
    out = build(reg, tmp_path_factory.mktemp("gated"))
    (out / "evals" / "retrieval_cases.jsonl").write_text(
        json.dumps({"id": "c1", "query": "alpha", "relevant": ["doc-1", "doc-9"]})
        + "\n"
    )
    (out / "app" / "components" / "retrieval.py").write_text(
        "def run(query, top_k=8):\n"
        "    return [{'id': 'doc-1'}]\n"
    )
    result = run_eval(out, "--min-recall", "0.9")
    assert result.returncode == 1
    assert "fix retrieval" in result.stderr


# --- audit pins: the resolver against every realization shape -------------


CASE = json.dumps({"id": "c1", "query": "alpha", "relevant": ["doc-1"]}) + "\n"


def test_a_wired_module_level_instance_is_used_not_a_fresh_one(
    reg, tmp_path_factory
):
    """Deployments wire state (an index, a connection) into an instance
    once. Constructing a fresh instance per call measured an empty
    retriever and blamed the index -- the exact misdiagnosis the walk
    exists to prevent."""
    out = build(reg, tmp_path_factory.mktemp("instance"))
    (out / "evals" / "retrieval_cases.jsonl").write_text(CASE)
    (out / "app" / "components" / "retrieval.py").write_text(
        "class Retrieval:\n"
        "    def __init__(self):\n"
        "        self.docs = []\n"
        "    def index(self, docs):\n"
        "        self.docs = docs\n"
        "    def retrieve(self, query, k):\n"
        "        return self.docs[:k]\n"
        "\n"
        "retriever = Retrieval()\n"
        "retriever.index([{'id': 'doc-1'}])\n"
    )
    result = run_eval(out)
    assert result.returncode == 0, result.stderr
    assert "100.0%" in result.stdout


def test_a_class_run_shape_is_called_with_query_and_top_k(
    reg, tmp_path_factory
):
    """hybrid-search, reranked-retrieval, llamaindex and the plain
    graph-expanded class all expose run(query, top_k=...). The resolver
    once called them with a payload dict, so four realizations could
    never pass their own CI gate."""
    out = build(reg, tmp_path_factory.mktemp("classrun"))
    (out / "evals" / "retrieval_cases.jsonl").write_text(CASE)
    (out / "app" / "components" / "retrieval.py").write_text(
        "class Retrieval:\n"
        "    def run(self, query, top_k=8):\n"
        "        assert isinstance(query, str), f'query is {type(query)}'\n"
        "        return [{'id': 'doc-1'}][:top_k]\n"
    )
    result = run_eval(out)
    assert result.returncode == 0, result.stderr
    assert "100.0%" in result.stdout


def test_duplicate_relevant_ids_do_not_inflate_recall(reg, tmp_path_factory):
    out = build(reg, tmp_path_factory.mktemp("dupes"))
    (out / "evals" / "retrieval_cases.jsonl").write_text(
        json.dumps({"id": "c1", "query": "alpha",
                    "relevant": ["doc-1", "doc-1", "doc-9"]}) + "\n"
    )
    (out / "app" / "components" / "retrieval.py").write_text(
        "def run(query, top_k=8):\n"
        "    return [{'id': 'doc-1'}]\n"
    )
    result = run_eval(out)
    assert "50.0%" in result.stdout, result.stdout


def test_a_result_with_no_ids_is_an_error_not_a_silent_zero(
    reg, tmp_path_factory
):
    """A mis-wired retriever returning the wrong shape used to score 0 and
    dilute the mean while CI stayed green."""
    out = build(reg, tmp_path_factory.mktemp("shape"))
    (out / "evals" / "retrieval_cases.jsonl").write_text(CASE)
    (out / "app" / "components" / "retrieval.py").write_text(
        "def run(query, top_k=8):\n"
        "    return {'answer': 'doc-1'}\n"
    )
    result = run_eval(out)
    assert result.returncode == 1
    assert "no id-bearing" in result.stderr


def test_a_path_contract_retrieval_gets_no_recall_gate(reg, tmp_path):
    """graph-retrieval answers path queries (from/to) and returns a path,
    not a ranking. Grading it on recall@K shipped a CI gate that could
    never pass, however well the system worked."""
    out = build(reg, tmp_path, values=dict(
        output_shape="freeform", input_format="documents",
        query_pattern="multi_hop", corpus_size=200_000,
        latency_budget_ms=800, external_systems=2,
        recall_span="within_session",
        operates_after_handover="platform_team", cheap_path_coverage=0.99,
    ))
    assert not (out / "evals" / "retrieval.py").exists()
    ci = (out / ".github" / "workflows" / "ci.yml").read_text()
    assert "evals/retrieval.py" not in ci
    diagnosis = (out / "ops" / "diagnosis.md").read_text()
    assert "evals/retrieval.py" not in diagnosis
    # The evidence step itself stays: there is still a retrieval layer to
    # inspect, just not one a recall number can grade.
    assert "recall, not reasoning" in diagnosis
