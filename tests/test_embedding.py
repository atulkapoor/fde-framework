"""Where embeddings are computed, decided rather than asked.

It was a dimension nothing acted on -- the framework put the question to a
client and then ignored the answer. It is a real decision with a real
constraint, so it becomes a component the framework decides.
"""

from pathlib import Path

import pytest

from fde.decide import decide_component
from fde.decompose import decompose
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


def test_a_lexical_only_system_needs_no_embeddings(reg):
    """The cheapest embedding is none. A keyword search does not have vectors
    to place anywhere."""
    graph = decompose(profile(output_shape="structured", query_pattern="lookup"), reg)
    assert "embedding" not in graph.components


def test_semantic_retrieval_brings_it_into_scope(reg):
    graph = decompose(profile(output_shape="freeform", query_pattern="comparative"), reg)
    assert "embedding" in graph.components


def test_data_that_cannot_leave_computes_embeddings_locally(reg):
    """An embedding is recoverable to its source, so sending one to a vendor is
    sending the text. 'We only send vectors' is not a defence."""
    decision = decide_component(
        "embedding", dict(output_shape="freeform", data_residency="cannot_leave"), reg
    )
    assert decision.approach == "local-embedding"


def test_an_air_gap_rules_out_a_hosted_embedding_service(reg):
    decision = decide_component(
        "embedding", dict(output_shape="freeform", hosting="air-gapped"), reg
    )
    assert decision.approach != "managed-embedding"


def test_data_free_to_move_takes_the_simpler_option(reg):
    decision = decide_component(
        "embedding", dict(output_shape="freeform", data_residency="may_leave"), reg
    )
    assert decision.approach == "managed-embedding"


def test_the_rejection_names_the_constraint(reg):
    decision = decide_component(
        "embedding", dict(output_shape="freeform", data_residency="cannot_leave"), reg
    )
    reasons = " ".join(r.reason for r in decision.rejected)
    assert "data_residency" in reasons


def test_the_question_is_no_longer_put_to_anybody(reg):
    """Asking about something no decision depends on wastes the one meeting you
    get. It is decided now, so it is not asked."""
    assert "embeddings" not in reg.dimensions


def test_no_dimension_is_asked_that_nothing_acts_on(reg):
    """The gap that started this, closed and kept closed."""
    from fde.graph import find_gaps

    inert = [g.detail for g in find_gaps(reg) if g.kind == "inert_dimension"]
    assert not inert, f"asked and unused: {inert}"


def test_an_embedding_store_inherits_the_residency_of_its_source(reg):
    """The consequence that matters for placement, not just for the vendor
    choice."""
    graph = decompose(
        profile(output_shape="freeform", query_pattern="comparative",
                data_residency="cannot_leave"), reg
    )
    assert "embedding" in graph.components
    assert "governance" in graph.components
