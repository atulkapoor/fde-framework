"""`fde start` and `fde status` -- the FDE's view of an engagement in progress."""

from typer.testing import CliRunner

from fde.cli import app

runner = CliRunner()
STATEMENT = "Extract fields from invoice PDFs. Data cannot leave the client environment."


def test_start_creates_an_engagement(tmp_path):
    r = runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    assert r.exit_code == 0
    assert (tmp_path / "acme" / "facts").is_dir()


def test_start_accepts_a_statement_but_does_not_require_one(tmp_path):
    assert runner.invoke(app, ["start", "a", "--base", str(tmp_path)]).exit_code == 0
    r = runner.invoke(app, ["start", "b", "--base", str(tmp_path), "--statement", STATEMENT])
    assert r.exit_code == 0
    assert (tmp_path / "b" / "statements" / "001.md").exists()


def test_start_refuses_to_overwrite(tmp_path):
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    r = runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    assert r.exit_code != 0 and "already exists" in r.output


def test_status_on_a_fresh_engagement_says_nothing_is_known(tmp_path):
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    r = runner.invoke(app, ["status", str(tmp_path / "acme")])
    assert r.exit_code == 0 and "nothing recorded yet" in r.output


def test_status_reports_resolved_dimensions_and_who_said_them(tmp_path):
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    (tmp_path / "acme" / "facts" / "0001-sponsor.yaml").write_text(
        "session_id: 0001-sponsor\n"
        "respondent: {role: sponsor, name: A. Sponsor}\n"
        "facts:\n  - {dimension: peak_qps, value: 40, provenance: interview}\n"
    )
    r = runner.invoke(app, ["status", str(tmp_path / "acme")])
    assert "peak_qps" in r.output
    assert "A. Sponsor" in r.output and "sponsor" in r.output  # name and role both


def test_status_surfaces_disagreements_prominently(tmp_path):
    """The most valuable thing discovery produces must not be buried."""
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    facts = tmp_path / "acme" / "facts"
    facts.joinpath("0001-sponsor.yaml").write_text(
        "session_id: '0001'\nrespondent: {role: sponsor}\n"
        "facts:\n  - {dimension: latency_budget_ms, value: 5000, provenance: interview}\n"
    )
    facts.joinpath("0002-user.yaml").write_text(
        "session_id: '0002'\nrespondent: {role: user}\n"
        "facts:\n  - {dimension: latency_budget_ms, value: 1000, provenance: interview}\n"
    )
    r = runner.invoke(app, ["status", str(tmp_path / "acme")])
    assert "unresolved" in r.output.lower()
    assert "5000" in r.output and "1000" in r.output
