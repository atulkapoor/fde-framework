"""Production grade, measured: the scorecard runs what a deliverable can
prove about itself and writes the numbers down, with a verdict that is a
count of rows rather than an adjective.

Built on the same labelled build the acceptance suite uses, because the
scorecard is only worth what it can catch: a constant classifier, a
missing exam record, a scaffold left in the register."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from fde.architect import architect
from fde.emit import emit
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry
from fde.scorecard import render, score

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"
LABELS = ("refund", "escalate", "reply")
VOCAB = {
    "refund": ["charged twice", "double charge", "money back", "overcharged",
               "fee never agreed"],
    "escalate": ["legal action", "ombudsman", "regulator", "lawyer",
                 "formal complaint"],
    "reply": ["how do I", "where can I", "what is the", "please explain",
              "which form"],
}


def pairs_file(path: Path, n: int = 48, offset: int = 0) -> Path:
    rows = []
    for i in range(n):
        label = LABELS[i % 3]
        rows.append({"id": f"c{offset + i}", "verified": True,
                     "input": f"Case {offset + i}: {VOCAB[label][(i + offset) % 5]} on my "
                              f"account statement, ticket {1000 + offset + i}.",
                     "output": {"decision": label}})
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


@pytest.fixture(scope="module")
def labelled(tmp_path_factory):
    reg = load_registry(FRAMEWORK)
    out = tmp_path_factory.mktemp("scorecard")
    pairs = out.parent / "scorecard-pairs.jsonl"
    pairs_file(pairs)
    profile = Profile()
    profile.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in dict(
        output_shape="decision", input_format="text", corpus_size=5_000,
        data_residency="may_leave", hosting="customer-vpc", external_systems=3,
        human_waiting="no", query_pattern="lookup", recall_span="within_turn").items()])
    emit(architect(profile, reg), out, registry=reg, pairs_path=pairs)
    return out


def rows_of(card) -> dict[str, object]:
    return {r.property: r for r in card.rows}


def test_the_scorecard_measures_and_writes(labelled, tmp_path):
    holdout = pairs_file(tmp_path / "holdout.jsonl", n=36, offset=500)
    card = score(labelled, holdout_path=holdout, timeout=300)
    rows = rows_of(card)
    assert rows["own tests"].holds is True
    assert rows["lint"].holds is True
    assert rows["exam: golden"].holds is True and "in-sample" in rows["exam: golden"].measured
    assert rows["exam record"].holds is True
    assert rows["holdout"].holds is True and "majority" in rows["holdout"].measured
    assert rows["holdout: sample size"].holds is True  # 36 >= the protocol floor
    assert rows["edge: boots"].holds is True
    assert rows["edge: identity"].holds is True
    assert rows["edge: forged result"].holds is True
    assert rows["edge: forged identity"].holds is True
    assert rows["environment"].holds is True
    assert rows["risk register: scaffolds"].holds is True
    assert rows["training path"].holds is None  # no train/ in this build
    assert "of" in card.verdict and "measured properties hold" in card.verdict
    written = (labelled / "SCORECARD.md").read_text()
    assert written.startswith("# Scorecard") and "| exam: golden |" in written
    record = json.loads((labelled / "scorecard.json").read_text())
    assert record["verdict"] == card.verdict
    assert not (labelled / "scorecard-harness.json").exists()


def test_a_constant_classifier_does_not_hold(labelled, tmp_path):
    out = tmp_path / "constant"
    shutil.copytree(labelled, out, ignore=shutil.ignore_patterns("__pycache__"))
    (out / "app" / "components" / "reasoning.py").write_text(
        "class Reasoning:\n"
        "    def run(self, payload):\n"
        "        return {**payload, 'decision': 'refund', 'decided_by': 'constant'}\n"
    )
    card = score(out, timeout=300, probe_edge=False)
    rows = rows_of(card)
    assert rows["exam: golden"].holds is False
    assert rows["exam: verdict"].holds is False
    assert any(r.property == "exam: golden" for r in card.failing)
    assert "## Not holding" in render(card)


def test_an_edited_exam_is_caught_by_the_record(labelled, tmp_path):
    out = tmp_path / "edited"
    shutil.copytree(labelled, out, ignore=shutil.ignore_patterns("__pycache__"))
    with (out / "evals" / "golden.jsonl").open("a") as handle:
        handle.write(json.dumps({"id": "late", "input": "a late case about a fee",
                                 "output": {"decision": "refund"}}) + "\n")
    card = score(out, timeout=300, probe_edge=False)
    rows = rows_of(card)
    assert rows["exam record"].holds is False and "golden" in rows["exam record"].measured


def test_a_holdout_that_is_not_the_recorded_one_is_named(labelled, tmp_path):
    other = pairs_file(tmp_path / "other.jsonl", n=36, offset=900)
    card = score(labelled, holdout_path=other, timeout=300, probe_edge=False)
    rows = rows_of(card)
    # This build recorded no engagement holdout (emitted straight from pairs),
    # so the digest row is absent rather than falsely reassuring.
    assert "holdout: the file on record" not in rows
    assert rows["holdout"].holds is True


def test_what_cannot_be_measured_is_not_counted(labelled):
    card = score(labelled, timeout=300, probe_edge=False)
    rows = rows_of(card)
    assert rows["holdout"].holds is None
    assert all(r.holds is not None for r in card.measured)
    assert len(card.measured) < len(card.rows)
