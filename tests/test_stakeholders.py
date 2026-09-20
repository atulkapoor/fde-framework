"""The stakeholder map is read off the record: sessions carry roles and
names, signatures carry `--by`, and the roles nobody has asked are named."""

from __future__ import annotations

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import Session, load_engagement, start_engagement
from fde.models.respondent import Respondent, Role
from fde.stakeholders import add, build, render

runner = CliRunner()


def engagement(tmp_path):
    start_engagement(tmp_path, "acme", statement="Decide each claim.")
    return load_engagement(tmp_path / "acme")


def test_roles_heard_named_and_signed_come_off_the_record(tmp_path):
    eng = engagement(tmp_path)
    eng.append(Session(session_id="0001-admin",
                       respondent=Respondent(role=Role.ADMIN, name="Dev Patel"), facts=[]))
    eng.record_data_access("read replica returned 14 rows", "2026-09-01", by="Dev Patel")
    eng.record_security_review("infosec walked the data paths", "2026-09-02")
    add(eng, "Priya Rao", "sponsor", "budget and go-live", at="2026-09-01")
    eng.record_deployed("client VPC", "2026-09-10", by="Priya Rao")
    stakeholders = build(eng)
    by_role = {row.role: row for row in stakeholders.rows}
    assert by_role["admin"].heard and by_role["admin"].heard_from == ["Dev Patel"]
    assert by_role["admin"].signed == ["data_access (2026-09-01)"]
    assert by_role["sponsor"].named == ["Priya Rao"] and not by_role["sponsor"].heard
    assert by_role["sponsor"].signed == ["deployed (2026-09-10)"]
    assert stakeholders.unheard == ["sponsor", "eval_owner", "user", "skeptic"]
    assert stakeholders.unsigned == ["security_review (2026-09-02)"]
    text = render(stakeholders, "acme")
    assert "never heard: fde ask <eng> --role skeptic" in text
    assert "nobody's name on it: security_review" in text


def test_a_person_outside_the_five_roles_is_listed_apart(tmp_path):
    eng = engagement(tmp_path)
    add(eng, "Sam Lee", "procurement", "the contract")
    stakeholders = build(eng)
    assert [p.name for p in stakeholders.others] == ["Sam Lee"]
    assert "outside the five roles: Sam Lee (procurement)" in render(stakeholders, "acme")


def test_the_commands_record_and_render(tmp_path):
    engagement(tmp_path)
    root = str(tmp_path / "acme")
    assert runner.invoke(app, ["stakeholder", root, "add", "--name", "Priya Rao",
                               "--role", "sponsor", "--stake", "budget"]).exit_code == 0
    refused = runner.invoke(app, ["stakeholder", root, "add", "--role", "sponsor"])
    assert refused.exit_code == 1 and "needs --name" in refused.output
    assert runner.invoke(app, ["deployed", root, "--note", "client VPC",
                               "--by", "Priya Rao"]).exit_code == 0
    shown = runner.invoke(app, ["stakeholders", root])
    assert shown.exit_code == 0, shown.output
    assert "Priya Rao" in shown.output and "signed:" in shown.output and "deployed" in shown.output


def test_waivers_and_reviews_carry_the_signer_when_given(tmp_path):
    engagement(tmp_path)
    root = str(tmp_path / "acme")
    assert runner.invoke(app, ["data-access", root, "--note", "replica returned 14 real rows",
                               "--by", "Dev Patel"]).exit_code == 0
    assert runner.invoke(app, ["security-review", root, "--note", "infosec walked the paths",
                               "--by", "Dev Patel"]).exit_code == 0
    waived = runner.invoke(app, ["waive", root, "client_readiness", "--reason", "owner named",
                                 "--by", "Priya Rao"])
    assert waived.exit_code == 0, waived.output
    state = load_engagement(tmp_path / "acme")._raw_gate_state()
    assert state["data_access"]["by"] == "Dev Patel"
    assert state["security_review"]["by"] == "Dev Patel"
    assert state["overrides"][0]["by"] == "Priya Rao"
