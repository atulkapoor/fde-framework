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
