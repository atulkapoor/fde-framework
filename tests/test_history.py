"""The history is every dated entry on the record in order, with the
undated ones above it, one line each."""

from __future__ import annotations

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import Session, load_engagement, start_engagement
from fde.history import events
from fde.models.respondent import Respondent, Role
from fde.stakeholders import add

runner = CliRunner()


def test_events_are_ordered_and_signed(tmp_path):
    start_engagement(tmp_path, "acme", statement="Decide each claim.")
    eng = load_engagement(tmp_path / "acme")
    eng.append(Session(session_id="0001-admin",
                       respondent=Respondent(role=Role.ADMIN, name="Dev"), facts=[]))
    eng.record_deployed("client VPC", "2026-09-10", by="Priya")
    eng.record_data_access("14 rows", "2026-09-01")
    add(eng, "Priya", "sponsor", at="2026-09-03")
    dated, undated = events(eng)
    assert [e["kind"] for e in dated] == ["data access", "stakeholder", "deployed"]
    assert dated[-1]["by"] == "Priya"
    assert undated[0].startswith("statement v1: Decide each claim.")
    assert "session 0001-admin: 0 fact(s) from Dev" in undated


def test_the_command_prints_the_page(tmp_path):
    start_engagement(tmp_path, "acme", statement="Decide each claim.")
    root = str(tmp_path / "acme")
    runner.invoke(app, ["deployed", root, "--note", "client VPC", "--today", "2026-09-10"])
    result = runner.invoke(app, ["history", root])
    assert result.exit_code == 0, result.output
    assert "on the record, undated:" in result.output
    assert "2026-09-10  deployed" in result.output
