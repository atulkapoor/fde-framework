"""A traceback at a client site reads as the tool being broken.

Every failure a user can cause with a typo, a corrupt file or a wrong path
gets a one-line explanation and a non-zero exit -- never a stack trace, and
never a success that is quietly wrong.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fde.cli import app

runner = CliRunner()


def engagement(tmp_path):
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    return tmp_path / "acme"


def test_an_unknown_role_lists_the_real_ones(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["ask", str(root), "--role", "cto"])
    assert result.exit_code == 1
    assert "sponsor" in result.output and "admin" in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_a_typoed_path_is_an_error_not_an_empty_engagement(tmp_path):
    """`fde architect /nonexistent` once printed a full architecture decided
    from nothing. A wrong path must not look like a valid engagement."""
    for command in (["status"], ["architect"], ["retro"]):
        result = runner.invoke(app, [*command, str(tmp_path / "nowhere")])
        assert result.exit_code == 1, command
        assert "no engagement here" in result.output


def test_a_corrupt_session_file_names_itself(tmp_path):
    root = engagement(tmp_path)
    (root / "facts" / "0001-bad.yaml").write_text("::: not yaml {{{")
    result = runner.invoke(app, ["status", str(root)])
    assert result.exit_code == 1
    assert "0001-bad" in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_a_stray_file_in_statements_is_ignored(tmp_path):
    root = engagement(tmp_path)
    (root / "statements" / "notes.md").write_text("somebody's scratchpad")
    result = runner.invoke(app, ["status", str(root)])
    assert result.exit_code == 0


def test_malformed_registry_yaml_is_located_not_tracebacked(tmp_path):
    bad = tmp_path / "registry" / "dimensions"
    bad.mkdir(parents=True)
    (bad / "broken.md").write_text("---\nid: [unclosed\n---\nbody\n")
    result = runner.invoke(app, ["kb", "validate", "--root", str(tmp_path / "registry")])
    assert result.exit_code == 1
    assert "broken.md" in result.output


def test_a_corrupt_pdf_refuses_by_name(tmp_path):
    pytest.importorskip("pypdf")
    root = engagement(tmp_path)
    fake = tmp_path / "brief.pdf"
    fake.write_bytes(b"%PDF-1.4 not actually a pdf")
    result = runner.invoke(app, ["frame", str(root), "--file", str(fake)])
    assert result.exit_code == 1
    assert "brief.pdf" in result.output


def test_a_malformed_pairs_file_refuses_the_build_before_writing(tmp_path):
    """emit's own rule: validate everything before writing anything. The
    pairs file was validated last, after half the project was on disk."""
    import yaml

    root = engagement(tmp_path)
    (root / "facts" / "0001.yaml").write_text(
        "session_id: '0001'\nrespondent: {role: admin}\n"
        "facts:\n"
        "  - {dimension: output_shape, value: structured, provenance: artifact}\n"
        "  - {dimension: input_format, value: documents, provenance: artifact}\n"
    )
    (root / "artifacts" / "pairs.jsonl").write_text("{not json\n")

    baseline = tmp_path / "b.yaml"
    baseline.write_text(yaml.safe_dump({
        "volume": 1, "cycle_time_per_unit_seconds": 1, "labour_hours_per_week": 1,
        "rework_rate": 0, "exception_rate": 0, "error_rate": 0,
        "business_metric": "m", "sampled": True, "definitions_recorded": True,
    }))
    runner.invoke(app, ["baseline", str(root), "--file", str(baseline)])
    runner.invoke(app, ["data-access", str(root), "--note", "rows"])
    runner.invoke(app, ["waive", str(root), "client_readiness", "--reason", "soon"])

    out = tmp_path / "out"
    result = runner.invoke(app, ["build", str(root), "--out", str(out)])
    assert result.exit_code == 1
    assert "refused" in result.output
    assert not out.exists() or not any(Path(out).iterdir())
