"""Findings from the first full demonstration engagement (public SROIE data).

`fde build <bare-name>` resolved the engagement through _engagement but
built the pairs path from the raw argument, so a project emitted with an
empty golden set while sixty verified pairs sat on the engagement. The
harness's empty-exam refusal caught it at runtime; these pins catch it at
commit time, and the build receipt now counts its own exam so the gap is
visible in the same breath as "wrote project".
"""

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from fde.cli import app

FRAMEWORK = str(Path(__file__).resolve().parents[1] / "framework")

runner = CliRunner()

FACTS = """session_id: '0001'
respondent: {role: admin}
facts:
  - {dimension: output_shape, value: structured, provenance: artifact}
  - {dimension: input_format, value: documents, provenance: artifact}
  - {dimension: corpus_size, value: 200000, provenance: artifact}
  - {dimension: data_residency, value: cannot_leave, provenance: artifact}
  - {dimension: external_systems, value: 2, provenance: artifact}
"""


@pytest.fixture
def satisfied_engagement(tmp_path, monkeypatch):
    """A gates-passed engagement with verified pairs, addressed by BARE NAME
    from the directory that holds engagements/ -- the exact shape the
    demonstration ran."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["start", "acme"])
    root = tmp_path / "engagements" / "acme"
    (root / "facts" / "0001.yaml").write_text(FACTS)

    pairs = tmp_path / "pairs.jsonl"
    with pairs.open("w") as f:
        for i in range(45):
            f.write(json.dumps({
                "id": f"p{i}", "verified": True,
                "input": f"receipt {i} TOTAL 9.{i:02d}",
                "output": {"total": f"9.{i:02d}"},
            }) + "\n")
    ingest = runner.invoke(app, ["samples", "acme", "--file", str(pairs)])
    assert "golden" in ingest.output, ingest.output

    baseline = tmp_path / "baseline.yaml"
    baseline.write_text(yaml.safe_dump({
        "volume": 1000, "cycle_time_per_unit_seconds": 60,
        "labour_hours_per_week": 10, "rework_rate": 0.1,
        "exception_rate": 0.1, "error_rate": 0.1,
        "business_metric": "days", "sampled": True,
        "definitions_recorded": True,
    }))
    runner.invoke(app, ["baseline", "acme", "--file", str(baseline)])
    runner.invoke(app, ["data-access", "acme", "--note", "rows returned"])
    runner.invoke(app, ["waive", "acme", "client_readiness",
                        "--reason", "named next week"])
    runner.invoke(app, ["security-review", "acme",
                        "--note", "infosec walked the data paths"])
    return tmp_path


def test_a_bare_name_build_carries_the_verified_pairs(satisfied_engagement):
    out = satisfied_engagement / "project"
    result = runner.invoke(app, ["build", "acme", "--out", str(out), "--registry", FRAMEWORK])
    assert "wrote" in result.output, result.output
    golden = (out / "evals" / "golden.jsonl").read_text().splitlines()
    assert len([line for line in golden if line.strip()]) > 0, (
        "bare-name build emitted an empty golden set beside verified pairs"
    )


def test_the_build_receipt_counts_its_own_exam(satisfied_engagement):
    out = satisfied_engagement / "project"
    result = runner.invoke(app, ["build", "acme", "--out", str(out), "--registry", FRAMEWORK])
    assert "golden" in result.output and "adversarial" in result.output


def test_an_empty_exam_next_to_pairs_is_called_out(satisfied_engagement, tmp_path):
    """If no pair reaches the golden set while pairs exist on the engagement,
    the receipt says so instead of reading as a finished build."""
    root = satisfied_engagement / "engagements" / "acme"
    pairs_path = root / "artifacts" / "pairs.jsonl"
    rows = [json.loads(line) for line in pairs_path.read_text().splitlines()]
    for r in rows:
        r.pop("verified", None)
    pairs_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    out = satisfied_engagement / "project2"
    result = runner.invoke(app, ["build", "acme", "--out", str(out), "--registry", FRAMEWORK])
    assert "0 golden" in result.output
    assert "verified" in result.output or "verified" in (result.stderr or "")
