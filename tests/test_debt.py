"""Decision debt is read off the record: gates, waivers, guessed and
stated facts, disagreements, unsigned entries, unheard roles, incidents."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import Session, load_engagement, start_engagement
from fde.models.base import DimensionKind, Provenance
from fde.models.fact import Fact
from fde.models.respondent import Respondent, Role

runner = CliRunner()
STATEMENT = ("Extract fields from scanned supplier invoices; data cannot leave; "
             "200,000 documents, 8,000 verified; a person is waiting.")


def test_the_command_lists_what_nobody_has_settled(tmp_path):
    start_engagement(tmp_path, "acme", statement=STATEMENT)
    eng = load_engagement(tmp_path / "acme")
    eng.append(Session(session_id="0009-admin",
                       respondent=Respondent(role=Role.ADMIN, name="Dev"),
                       facts=[Fact("gpu_available", "true", Provenance.INTERVIEW,
                                   kind=DimensionKind.ENVIRONMENT)]))
    eng.record_waiver("client_readiness", "owner named next week", "2026-08-01",
                      against="Nobody has been named")
    eng.record_data_access("replica returned rows", "2026-09-01")
    (tmp_path / "acme" / "incidents.jsonl").write_text(json.dumps(
        {"id": "inc-001", "status": "open", "opened_at": "2026-08-15", "kind": "drift"}) + "\n")
    result = runner.invoke(app, ["debt", str(tmp_path / "acme"), "--as-of", "2026-09-20"])
    assert result.exit_code == 0, result.output
    out = result.output
    assert "blocking the build" in out and "gate           baseline_capture" in out
    assert "gate           outcome_contract" in out
    assert "waiver         client_readiness" in out and "50 day(s) AGING" in out
    assert "stated         gpu_available = true" in out and "measurable but not measured" in out
    assert "incident       inc-001" in out and "36 day(s) AGING" in out
    assert "unsigned       data_access (2026-09-01)" in out
    assert "unheard        sponsor has never been asked" in out
    assert "3 older than 30 days" in out and "2 unsigned" in out


def test_a_settled_record_has_little_debt(tmp_path):
    start_engagement(tmp_path, "acme", statement=STATEMENT)
    result = runner.invoke(app, ["debt", str(tmp_path / "acme")])
    assert result.exit_code == 0
    assert "decision debt as of" in result.output and "item(s)" in result.output
    assert Path(tmp_path / "acme" / "facts").is_dir()


def test_a_stated_fact_ages_from_the_day_its_session_was_recorded(tmp_path):
    start_engagement(tmp_path, "acme", statement=STATEMENT)
    eng = load_engagement(tmp_path / "acme")
    eng.append(Session(session_id="0009-admin", recorded_at="2026-06-01",
                       respondent=Respondent(role=Role.ADMIN, name="Dev"),
                       facts=[Fact("gpu_available", "true", Provenance.INTERVIEW,
                                   kind=DimensionKind.ENVIRONMENT)]))
    result = runner.invoke(app, ["debt", str(tmp_path / "acme"), "--as-of", "2026-09-21"])
    assert result.exit_code == 0, result.output
    assert "stated         gpu_available = true" in result.output
    assert "112 day(s) AGING" in result.output
    text = (tmp_path / "acme" / "facts" / "0009-admin.yaml").read_text()
    assert "recorded_at: '2026-06-01'" in text or "recorded_at: 2026-06-01" in text
