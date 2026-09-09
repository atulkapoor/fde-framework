"""Pins from the 0.1.4 fresh-eyes audit.

Three independent auditors (adversarial code review, stranger-path DX,
docs-truth) ran against the 0.1.4 release; every code finding that survived
verification is pinned here or in test_retrieval_eval.py, so none of them
can quietly return.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fde.architect import architect
from fde.cli import app
from fde.decide import decide_component
from fde.emit import _acceptance, emit
from fde.gates import input_status
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def profile(**values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    return p


# --- the fingerprint answers the question it prints beside ----------------


def test_topology_changes_the_fingerprint(reg):
    """Two profiles with the same approach set but different topologies
    build byte-different projects; a fingerprint calling them identical
    was hashing a narrower thing than the one it stands beside."""
    base = dict(output_shape="structured", input_format="documents",
                query_pattern="lookup", corpus_size=200_000,
                external_systems=1)
    on_prem = architect(profile(**base, hosting="on-prem"), reg)
    vpc = architect(profile(**base, hosting="customer-vpc"), reg)
    assert on_prem.topology != vpc.topology
    assert on_prem.fingerprint() != vpc.fingerprint()


def test_same_design_same_fingerprint(reg):
    """The original property survives: different profiles, same decisions,
    same topology -- same answer."""
    base = dict(output_shape="structured", input_format="documents",
                query_pattern="lookup", corpus_size=200_000,
                external_systems=1, hosting="on-prem")
    one = architect(profile(**base), reg)
    two = architect(profile(**base, latency_budget_ms=800), reg)
    if one.decisions.decided_fingerprint() == two.decisions.decided_fingerprint():
        assert one.fingerprint() == two.fingerprint()


# --- acceptance.md tells the truth about its own engagement ---------------


def test_acceptance_does_not_claim_a_name_the_waiver_erased(reg):
    arch = architect(profile(output_shape="structured",
                             input_format="documents",
                             external_systems=1), reg)
    body = _acceptance(arch, 12, waived={"client_readiness"})
    assert "NOT yet named" in body
    assert "gate holds their name" not in body


def test_acceptance_with_an_empty_golden_set_does_not_cite_zero_cases(reg):
    arch = architect(profile(output_shape="structured",
                             input_format="documents",
                             external_systems=1), reg)
    body = _acceptance(arch, 0, waived=set())
    assert "seen those 0" not in body
    assert "golden set is empty" in body


# --- the interview asks a multi-valued question once per session ----------


def test_a_multi_valued_answer_retires_its_question_for_the_session(tmp_path):
    """input_format never enters the answer space (a second value is a peer,
    not a contradiction), so the space alone re-offers the question the
    moment the loop comes round -- accepted used to mean asked again."""
    runner = CliRunner()
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    result = runner.invoke(
        app, ["ask", str(tmp_path / "acme"), "--role", "user"],
        input="text\n" + "\n" * 25,
    )
    question = "What arrives, and in what form?"
    assert result.output.count(question) == 1, result.output


# --- every gate names a clearing command ----------------------------------


def test_the_evaluability_remedy_names_its_clearing_command(reg):
    status = input_status(
        profile(output_shape="freeform", data_residency="cannot_leave",
                input_format="documents"),
        registry=reg,
    )
    gate = next(g for g in status.gates if g.name == "offline_evaluability")
    assert not gate.passed
    assert "fde waive" in gate.remedy


# --- a rejection names the unanswered question that could reverse it ------


def test_rejection_for_an_unanswered_dimension_says_which_question(reg):
    """multi_hop with churn unknown picks the full graph; the reader should
    see that one answer -- not a design change -- could admit the lighter
    variant."""
    decision = decide_component(
        "retrieval",
        dict(output_shape="freeform", query_pattern="multi_hop"),
        reg,
    )
    assert decision.approach == "graph-retrieval"
    rejected = next(r for r in decision.rejected
                    if r.id == "graph-expanded-retrieval")
    assert "unanswered: corpus_churn" in rejected.reason


# --- the emitted slo.md shows the baseline that was captured --------------


BASELINE = {
    "volume": {"value": 20000, "unit": "docs/month",
               "definition": "invoices received by AP"},
    "error_rate": {"value": 0.04, "unit": "ratio",
                   "definition": "wrong amount or vendor posted"},
    "sampled": {"n": 40, "method": "random invoices across two months"},
}


def test_a_captured_baseline_reaches_the_emitted_slo(reg, tmp_path):
    arch = architect(profile(output_shape="structured",
                             input_format="documents", query_pattern="lookup",
                             corpus_size=200_000, external_systems=1,
                             hosting="on-prem"), reg)
    emit(arch, tmp_path, baseline=BASELINE)
    body = (tmp_path / "ops" / "slo.md").read_text()
    assert "Captured" in body and "Not captured" not in body
    assert "20000" in body and "invoices received by AP" in body
    assert "n=40" in body


def test_a_missing_baseline_still_says_so(reg, tmp_path):
    arch = architect(profile(output_shape="structured",
                             input_format="documents", query_pattern="lookup",
                             corpus_size=200_000, external_systems=1,
                             hosting="on-prem"), reg)
    emit(arch, tmp_path)
    assert "Not captured" in (tmp_path / "ops" / "slo.md").read_text()


# --- the qdrant graph templates, executed --------------------------------


class _Hit:
    def __init__(self, id, payload, score=1.0):
        self.id, self.payload, self.score = id, payload, score


class _FakeQdrant:
    """search() answers similarity for the designated seeds only;
    retrieve() only returns ids that exist, the way the real client behaves
    when a document has been deleted."""

    def __init__(self, store, seeds):
        self.store = store
        self.seeds = seeds

    def search(self, collection_name, query_vector, limit, with_payload):
        return [_Hit(i, self.store[i]) for i in self.seeds[:limit]]

    def retrieve(self, collection_name, ids, with_payload):
        return [_Hit(i, self.store[i]) for i in ids if i in self.store]


def _run_template(name, wire):
    from jinja2 import Template

    source = Template(
        (FRAMEWORK / "templates" / "retrieval" / name).read_text()
    ).render(component="retrieval", approach="x", stack="qdrant",
             rationale="r", class_name="Retrieval", interface="Retriever")
    namespace = {}
    exec(compile(source, name, "exec"), namespace)  # noqa: S102
    wire(namespace)
    return namespace["run"]("alpha")


def test_graph_retrieval_qdrant_actually_walks_its_graph():
    """The expansion comprehension yielded the frontier id instead of the
    neighbour, so the walk was dead code and graph retrieval silently
    degraded to vector search -- shipped that way since v0.1.3."""
    def wire(ns):
        ns["client"] = _FakeQdrant({
            "doc-1": {"entities": ["E1"]},
            "doc-7": {"entities": []},
        }, seeds=["doc-1"])
        ns["embed"] = lambda text: [0.0]
        ns["adjacency"] = {"E1": ["doc-7"]}
    results = _run_template("graph-retrieval.qdrant.py.j2", wire)
    assert any(r["id"] == "doc-7" and r["hop"] == 1 for r in results)


def test_graph_expanded_qdrant_survives_a_ghost_in_the_adjacency_map():
    """On a corpus that keeps changing, the adjacency map can name a chunk
    deleted since the last rebuild. Walking on from the ghost was a
    KeyError in the exact scenario this variant exists for."""
    def wire(ns):
        ns["client"] = _FakeQdrant({
            "doc-1": {"entities": ["E1"], "text": "a"},
            "doc-7": {"entities": ["E2"], "text": "b"},
            "doc-9": {"entities": [], "text": "c"},
        }, seeds=["doc-1"])
        ns["embed"] = lambda text: [0.0]
        ns["rerank"] = lambda query, text: 1.0
        ns["adjacency"] = {"E1": ["ghost-1", "doc-7"], "E2": ["doc-9"]}
    results = _run_template("graph-expanded-retrieval.qdrant.py.j2", wire)
    ids = {r["id"] for r in results}
    assert "doc-7" in ids and "doc-9" in ids  # hop 2 through the survivor
    assert "ghost-1" not in ids
