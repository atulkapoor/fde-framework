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

REPO = Path(__file__).resolve().parents[1]
FRAMEWORK = str(REPO / "framework")

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
    runner.invoke(app, ["outcome-contract", "acme", "--owner", "ops lead",
                     "--metric", "cycle_time", "--baseline", "180", "--unit", "s",
                     "--target", "60", "--method", "ticket timestamps",
                     "--window", "60 days after go-live"])

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


# --- a refusal writes nothing; a failure leaves nothing that looks like a build


def test_an_unknown_locale_is_refused_before_anything_is_written(satisfied_engagement):
    """The locale was once checked after the project and the prediction
    records had gone to disk, and the refusal said so: "refused after
    writing code". A reader of the fifteenth outside audit found it in
    the source. A refusal that leaves a finished-looking project behind is
    not a refusal."""
    root = satisfied_engagement / "engagements" / "acme"
    (root / "locale").write_text("atlantis-2099")
    out = satisfied_engagement / "project"
    result = runner.invoke(app, ["build", "acme", "--out", str(out), "--registry", FRAMEWORK])
    assert result.exit_code == 1
    assert "atlantis-2099" in result.output and "Nothing was written" in result.output
    assert not out.exists()
    assert not (root / "predictions.jsonl").exists()
    assert not (root / ".last-out").exists()
    assert not list(satisfied_engagement.glob(".project.building*"))


def test_a_writer_that_fails_midway_leaves_no_project_and_no_staging(satisfied_engagement,
                                                                     monkeypatch):
    from fde import emit as emitter

    def broken(out, *args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(emitter, "_write_smoke", broken)
    out = satisfied_engagement / "project"
    with pytest.raises(RuntimeError, match="disk full"):
        runner.invoke(app, ["build", "acme", "--out", str(out), "--registry", FRAMEWORK],
                      catch_exceptions=False)
    assert not out.exists()
    assert not list(satisfied_engagement.glob(".project.building*"))


def test_a_build_is_moved_into_place_whole_and_named_for_its_destination(satisfied_engagement):
    out = satisfied_engagement / "my_delivery"
    result = runner.invoke(app, ["build", "acme", "--out", str(out), "--registry", FRAMEWORK])
    assert "wrote" in result.output, result.output
    assert not list(satisfied_engagement.glob(".my_delivery.building*"))
    assert 'name = "my-delivery"' in (out / "pyproject.toml").read_text()


# --- the exam reaches the thing it examines


def test_pairs_the_design_cannot_read_refuse_the_build_before_it_is_written(satisfied_engagement):
    """The invoice example's text pairs were refused at the emitted
    pipeline's own door, and the build had said "wrote": every golden case
    scored as an input error, measuring nothing. A build whose exam cannot
    enter the pipeline is refused in staging."""
    root = satisfied_engagement / "engagements" / "acme"
    golden = root / "artifacts" / "pairs.jsonl"
    assert golden.exists(), "the fixture seeds pairs"
    cases = [json.loads(line) for line in golden.read_text().splitlines() if line.strip()]
    for case in cases:
        case["input"] = {"blob": case["input"]}  # a key no emitted contract reads
    golden.write_text("".join(json.dumps(c) + "\n" for c in cases))
    out = satisfied_engagement / "project"
    result = runner.invoke(app, ["build", "acme", "--out", str(out), "--registry", FRAMEWORK])
    assert result.exit_code == 1, result.output
    assert "the exam cannot enter the pipeline" in result.output
    assert "unknown keys ['blob']" in result.output
    assert not out.exists() and not list(satisfied_engagement.glob(".project.building*"))


def test_the_invoice_example_reaches_its_extraction_stage_and_says_ocr_went_unexercised(tmp_path,
                                                                                         monkeypatch):
    import subprocess
    import sys

    example = REPO / "examples" / "invoice-extraction"
    monkeypatch.chdir(tmp_path)
    for argv in (["start", "acme", "--statement",
                  "Extract structured fields from scanned supplier invoices."],
                 ["frame", "acme", "--file", str(example / "brief.md"), "--registry", FRAMEWORK],
                 ["samples", "acme", "--file", str(example / "pairs.jsonl")],
                 ["baseline", "acme", "--file", str(example / "baseline.yaml")],
                 ["data-access", "acme", "--note", "read replica returned 14 rows"],
                 ["security-review", "acme", "--note", "infosec reviewed data paths"],
                 ["waive", "acme", "client_readiness", "--reason", "eval owner named"],
                 ["outcome-contract", "acme", "--owner", "the AP director",
                  "--metric", "days_receipt_to_posting", "--baseline", "9", "--unit", "days",
                  "--target", "3", "--method", "posting dates", "--window", "90 days"]):
        result = runner.invoke(app, argv)
        assert result.exit_code == 0, (argv, result.output)
    built = runner.invoke(app, ["build", "acme", "--out", "project", "--registry", FRAMEWORK])
    assert "wrote project" in built.output, built.output
    assert "perception" in (tmp_path / "project" / "ARCHITECTURE.md").read_text()
    run = subprocess.run([sys.executable, "-m", "evals.harness"], cwd=tmp_path / "project",
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 1  # the extraction is a scaffold until fde implement
    assert "RefusedInput" not in run.stdout + run.stderr
    assert "entered as text supplied; the OCR stage was not exercised" in run.stderr
    assert '"source": "prediction"' in run.stdout
