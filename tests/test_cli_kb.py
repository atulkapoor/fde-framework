"""`fde kb` -- the first thing an FDE runs, and the first thing CI runs."""

from typer.testing import CliRunner

from fde.cli import app

runner = CliRunner()


def test_validate_exits_zero_on_a_clean_registry(framework):
    r = runner.invoke(app, ["kb", "validate", "--root", str(framework)])
    assert r.exit_code == 0


def test_validate_exits_nonzero_on_a_dangling_link(tmp_path):
    """CI must fail on this, not print a warning nobody reads."""
    from tests.test_registry import CASE, PATTERN, write

    write(tmp_path, "cases", "doc-extraction", CASE)
    write(tmp_path, "patterns", "supervisor-worker", PATTERN)  # stacks missing
    r = runner.invoke(app, ["kb", "validate", "--root", str(tmp_path)])
    assert r.exit_code != 0
    assert "langgraph" in r.output


def test_lenient_downgrades_link_errors_for_work_in_progress(tmp_path):
    from tests.test_registry import CASE, PATTERN, write

    write(tmp_path, "cases", "doc-extraction", CASE)
    write(tmp_path, "patterns", "supervisor-worker", PATTERN)
    r = runner.invoke(app, ["kb", "validate", "--root", str(tmp_path), "--lenient"])
    assert r.exit_code == 0


def test_a_schema_error_names_the_file_in_the_output(tmp_path):
    from tests.test_registry import write

    write(tmp_path, "stacks", "broken", "---\nid: broken\n---\n")
    r = runner.invoke(app, ["kb", "validate", "--root", str(tmp_path)])
    assert r.exit_code != 0 and "broken.md" in r.output


def test_gaps_reports_without_failing(framework):
    """Gaps are work items, not errors."""
    r = runner.invoke(app, ["kb", "gaps", "--root", str(framework)])
    assert r.exit_code == 0
