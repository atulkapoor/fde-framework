"""The rest of the plain implementations, each carrying its own trap.

Deterministic mapping fails loudly rather than producing a well-formed wrong
answer. Explainability is recorded at decision time because it cannot be
reconstructed afterwards. A metric is chosen from the cost of each error rather
than from convention. A fixed sequence stays enumerable.
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


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def project(reg, out, **values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    emit(architect(p, reg), out)
    return out


def run_in(project_dir, code):
    return subprocess.run(
        [sys.executable, "-c", code], cwd=project_dir, capture_output=True, text=True
    )


@pytest.fixture(scope="module")
def extraction(reg, tmp_path_factory):
    return project(
        reg, tmp_path_factory.mktemp("extract"),
        output_shape="structured", input_format="documents", query_pattern="lookup",
        corpus_size=200_000, labelled_count=8_000, data_residency="cannot_leave",
        hosting="air-gapped", external_systems=1, cheap_path_coverage=0.99,
        interpretability_required=True, latency_budget_ms=800,
        recall_span="within_session", operates_after_handover="platform_team",
    )


# --- deterministic mapping: fail loudly ----------------------------------


def test_a_field_it_cannot_map_is_reported_not_invented(extraction):
    """A well-formed answer with the wrong account number is worse than a
    refusal, because nothing downstream can tell it is wrong."""
    result = run_in(extraction, """
from app.components.representation import Representation
out = Representation().run({"records": [{"id": "1", "raw": {"Acct No": "GB29-1234"}}],
                            "contract": ["account", "total"]})
assert "total" in out["records"][0]["unmapped"]
assert "total" not in out["records"][0]["mapped"]
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_a_known_synonym_maps(extraction):
    result = run_in(extraction, """
from app.components.representation import Representation
r = Representation(synonyms={"account": ["acct no", "account number"]})
out = r.run({"records": [{"id": "1", "raw": {"Acct No": "GB29-1234"}}],
             "contract": ["account"]})
assert out["records"][0]["mapped"]["account"] == "GB29-1234"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_a_value_failing_its_validator_is_rejected_not_coerced(extraction):
    """Coercion is how a parser turns 4,230 into 4 and reports success."""
    result = run_in(extraction, """
from app.components.representation import Representation
r = Representation(synonyms={"total": ["amount"]},
                   validators={"total": lambda v: v.replace(",", "").isdigit()})
out = r.run({"records": [{"id": "1", "raw": {"Amount": "four thousand"}}],
             "contract": ["total"]})
assert out["records"][0]["rejected"]["total"]
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_the_batch_reports_how_much_it_could_map(extraction):
    result = run_in(extraction, """
from app.components.representation import Representation
r = Representation(synonyms={"account": ["acct no"]})
out = r.run({"records": [{"id": "1", "raw": {"Acct No": "X"}},
                         {"id": "2", "raw": {"Mystery": "Y"}}],
             "contract": ["account"]})
assert out["mapped_share"] == 0.5
print("ok")
""")
    assert result.returncode == 0, result.stderr


@pytest.fixture(scope="module")
def scoring(reg, tmp_path_factory):
    """A model makes the call, so inputs and outcome do not reconstruct it."""
    return project(
        reg, tmp_path_factory.mktemp("scoring"),
        output_shape="classification", input_format="structured_data",
        corpus_size=2_000_000, interpretability_required=True,
        latency_budget_ms=10, external_systems=1, data_residency="may_leave",
        hosting="customer-vpc", cheap_path_coverage=0.99,
        operates_after_handover="platform_team", human_waiting="yes",
    )


# --- explainability: recorded, not reconstructed -------------------------


def test_a_rule_based_decision_gets_a_replayable_log(extraction):
    """Replaying the rule against the recorded inputs reproduces the outcome
    exactly. That is a stronger explanation than any attribution, and it needs
    no model to produce."""
    result = run_in(extraction, """
from app.components.accountability import Accountability
a = Accountability()
a.record("c1", inputs={"amount": 100}, rule="amount > 50", outcome=True)
assert a.replay("c1", apply=lambda i: i["amount"] > 50)
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_a_model_decision_gets_attribution_instead(scoring):
    """Inputs and outcome do not reconstruct a model's reasoning, so a log of
    them is not an explanation however complete it looks."""
    result = run_in(scoring, """
from app.components.accountability import Accountability
assert hasattr(Accountability(), "explain")
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_a_decision_records_what_drove_it(scoring):
    """Reconstructing why afterwards is guesswork in a report's formatting."""
    result = run_in(scoring, """
from app.components.accountability import Accountability
a = Accountability()
a.explain("case-1", outcome="declined", drivers=[("balance", -0.4), ("tenure", 0.1)])
assert a.explanation("case-1")["drivers"][0][0] == "balance"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_an_explanation_names_the_largest_driver_first(scoring):
    """An explanation that buries the reason in position six is not one."""
    result = run_in(scoring, """
from app.components.accountability import Accountability
a = Accountability()
a.explain("c", outcome="declined", drivers=[("small", 0.05), ("large", -0.9)])
assert a.explanation("c")["drivers"][0][0] == "large"
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_a_decision_without_an_explanation_is_findable(scoring):
    """In a system that promised explanations, the unexplained decision is
    exactly what an auditor asks about."""
    result = run_in(scoring, """
from app.components.accountability import Accountability
a = Accountability()
a.explain("c1", outcome="ok", drivers=[("x", 1.0)])
assert a.unexplained(["c1", "c2"]) == ["c2"]
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_the_explanation_reads_as_a_sentence(scoring):
    """Somebody outside the team has to read this, months later."""
    result = run_in(scoring, """
from app.components.accountability import Accountability
a = Accountability()
a.explain("c", outcome="declined", drivers=[("balance", -0.9), ("tenure", 0.2)])
said = a.narrate("c")
assert "balance" in said and "against" in said
print(said)
""")
    assert result.returncode == 0, result.stderr
