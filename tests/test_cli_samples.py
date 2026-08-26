"""`fde samples` -- the contract, the metric and the golden set, from examples."""

import json

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement

runner = CliRunner()

PAIRS = [
    {"id": "a", "input": "Total due: 4230", "verified": True, "layout": "boxed",
     "output": {"gains": 4230.0, "account": "****4471"}},
    {"id": "b", "input": "ST ... 1100", "verified": True, "layout": "dotted",
     "output": {"gains": 1100.0, "account": "****9931"}},
    {"id": "c", "input": "scan", "verified": False, "layout": "boxed",
     "output": {"gains": 0.0, "account": "****0001"}},
]


def engagement(tmp_path):
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    path = tmp_path / "pairs.jsonl"
    path.write_text("\n".join(json.dumps(p) for p in PAIRS))
    return tmp_path / "acme", path


def test_the_contract_is_shown_field_by_field(tmp_path):
    root, pairs = engagement(tmp_path)
    result = runner.invoke(app, ["samples", str(root), "--file", str(pairs)])
    assert result.exit_code == 0
    assert "gains" in result.output and "account" in result.output


def test_a_sensitive_field_is_named_as_such(tmp_path):
    """This is what pins it inside a boundary later, so it has to be visible
    while somebody can still say it is wrong."""
    root, pairs = engagement(tmp_path)
    result = runner.invoke(app, ["samples", str(root), "--file", str(pairs)])
    assert "identifier" in result.output


def test_the_metric_is_reported_rather_than_chosen_later(tmp_path):
    root, pairs = engagement(tmp_path)
    result = runner.invoke(app, ["samples", str(root), "--file", str(pairs)])
    assert "field_exact_match" in result.output


def test_too_few_pairs_is_said_out_loud(tmp_path):
    root, pairs = engagement(tmp_path)
    result = runner.invoke(app, ["samples", str(root), "--file", str(pairs)])
    assert "2 verified pairs" in result.output


def test_the_pairs_settle_the_shape_and_never_the_counts(tmp_path):
    """Counts stay questions: the file cannot know whether it is the whole
    labelled set, and a stated number must not be outvoted by a line count."""
    root, pairs = engagement(tmp_path)
    runner.invoke(app, ["samples", str(root), "--file", str(pairs)])
    profile = load_engagement(root).profile
    assert profile.get("output_shape") == "structured"
    assert profile.get("labelled_count") is None
    assert profile.get("corpus_size") is None


def test_the_pairs_are_kept_so_the_build_can_use_them(tmp_path):
    root, pairs = engagement(tmp_path)
    runner.invoke(app, ["samples", str(root), "--file", str(pairs)])
    assert (root / "artifacts" / "pairs.jsonl").exists()


def test_contradictory_pairs_are_refused_and_nothing_is_recorded(tmp_path):
    root, _ = engagement(tmp_path)
    bad = tmp_path / "bad.jsonl"
    bad.write_text("\n".join(json.dumps(p) for p in [
        {"id": "x", "input": "same", "verified": True, "output": {"total": 1}},
        {"id": "y", "input": "same", "verified": True, "output": {"total": 2}},
    ]))
    result = runner.invoke(app, ["samples", str(root), "--file", str(bad)])
    assert result.exit_code != 0
    assert "specification question" in result.output
    assert not (root / "artifacts" / "pairs.jsonl").exists()


def test_a_stated_count_survives_a_later_sample_file(tmp_path):
    """The bug this guards against: frame extracts corpus_size=200,000 from
    the brief, then a three-line sample file arrives and silently overwrites
    it with 3 -- flipping every decision gated on labels or volume."""
    root, pairs = engagement(tmp_path)
    runner.invoke(app, [
        "frame", str(root),
        "--text", "About 200,000 documents. Around 8,000 labelled examples exist.",
    ])
    runner.invoke(app, ["samples", str(root), "--file", str(pairs)])
    profile = load_engagement(root).profile
    assert profile.get("corpus_size") == 200_000
    assert profile.get("labelled_count") == 8_000
