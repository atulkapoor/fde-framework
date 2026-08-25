"""`fde override` and `fde retro` -- capturing what an engagement taught."""

import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from fde.cli import app

runner = CliRunner()
FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"

FACTS = """session_id: '0001'
respondent: {role: admin}
facts:
  - {dimension: output_shape, value: structured, provenance: artifact}
  - {dimension: input_format, value: documents, provenance: artifact}
  - {dimension: corpus_size, value: 200000, provenance: artifact}
  - {dimension: data_residency, value: cannot_leave, provenance: artifact}
  - {dimension: external_systems, value: 2, provenance: artifact}
"""


def engagement(tmp_path):
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    (tmp_path / "acme" / "facts" / "0001.yaml").write_text(FACTS)
    return tmp_path / "acme"


def framework_hash():
    digest = hashlib.sha256()
    for path in sorted(FRAMEWORK.rglob("*")):
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_an_override_is_recorded_without_complaint(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, [
        "override", str(root), "--component", "governance",
        "--choose", "audit-only", "--because", "client accepts the risk",
    ])
    assert result.exit_code == 0
    assert "recorded" in result.output


def test_the_override_names_the_rule_it_overrode(tmp_path):
    """'They chose something else' does not say which rule was wrong."""
    root = engagement(tmp_path)
    runner.invoke(app, [
        "override", str(root), "--component", "governance",
        "--choose", "audit-only", "--because", "risk accepted",
    ])
    recorded = json.loads((root / "overrides.jsonl").read_text().splitlines()[0])
    assert recorded["overrode_rule"] == "boundary-and-audit"
    assert recorded["blocking"] is False


def test_an_override_against_a_hard_constraint_is_flagged_not_refused(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, [
        "override", str(root), "--component", "serving",
        "--choose", "managed-api", "--because", "no GPU budget",
    ])
    assert result.exit_code == 0
    assert "conflicts" in result.output
    assert "risks" in result.output


def test_a_retro_emits_a_case(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["retro", str(root), "--outcome", "delivered",
                                 "--today", "2026-08-25"])
    assert result.exit_code == 0
    assert (root / "case.json").exists()


def test_the_case_does_not_name_the_client(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    case = json.loads((root / "case.json").read_text())
    assert "acme" not in case["id"].lower()
    assert case["sanitization"] == "reviewed"


def test_the_retro_says_the_evidence_is_strong_and_why(tmp_path):
    """Calibration has no counterfactual, which is what makes it worth more
    than a replay."""
    root = engagement(tmp_path)
    result = runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    assert "strong" in result.output
    assert "counterfactual" in result.output


def test_a_retro_changes_no_rules(tmp_path):
    """Capture only. Revising on a handful of engagements would be borrowing
    rigour rather than having it."""
    root = engagement(tmp_path)
    before = framework_hash()
    runner.invoke(app, ["retro", str(root), "--outcome", "delivered",
                        "--today", "2026-08-25"])
    assert framework_hash() == before


def test_the_retro_says_so_out_loud(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    assert "Nothing in framework/ was changed" in result.output


def test_the_practice_metric_is_captured(tmp_path):
    """Is the Nth solution faster than the first, and how much came off the
    shelf. The denominator revision is eventually measured against."""
    root = engagement(tmp_path)
    runner.invoke(app, ["retro", str(root), "--days", "21", "--today", "2026-08-25"])
    case = json.loads((root / "case.json").read_text())
    assert case["practice"]["days"] == 21
    assert case["practice"]["reused"]


def test_overriding_where_nothing_was_recommended_says_so(tmp_path):
    """A component chosen where the framework had no opinion is a gap in the
    corpus, not a disagreement with it. Those are different signals."""
    root = engagement(tmp_path)
    result = runner.invoke(app, [
        "override", str(root), "--component", "serving",
        "--choose", "managed-api", "--because", "no GPU budget",
    ])
    assert "gap in the corpus" in result.output
