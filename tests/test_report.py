"""The decision brief: one document, read off the record, for the person
who has to act on the decision and is not at the terminal."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement, start_engagement
from fde.stop import record as record_conditions

runner = CliRunner()
STATEMENT = "Route each support message to one of 77 queues; customer data may not leave AWS."


def test_a_fresh_engagement_gets_a_brief_with_every_section_and_the_statement(tmp_path):
    start_engagement(tmp_path, "acme", statement=STATEMENT)
    result = runner.invoke(app, ["report", str(tmp_path / "acme"), "--today", "2026-10-12"])
    assert result.exit_code == 0, result.output
    brief = tmp_path / "acme" / "artifacts" / "REPORT.md"
    assert brief.exists() and str(brief) in result.output
    text = brief.read_text()
    assert text.startswith("# acme: decision brief")
    for heading in ("The problem as stated", "Where the engagement stands",
                    "What the record knows, and who said it",
                    "The number this system exists to move", "The design, with its reasons",
                    "What the design rests on, and what was accepted", "Decision debt",
                    "What would stop this", "The next decision"):
        assert f"## {heading}" in text, heading
    assert f"> {STATEMENT}" in text and "<!--" not in text
    assert "blocked by" in text and "no stop conditions on record" in text
    assert "next: fde " in text and "Rejected alternatives" in text
    # The assumptions are listed once, under the risks, not twice.
    assert text.count("accelerator: not stated") == 1
    assert "### Unanswered assumptions" in text and "### Assumptions" not in text


def test_the_brief_is_deterministic_for_a_date_and_goes_where_asked(tmp_path):
    start_engagement(tmp_path, "acme", statement=STATEMENT)
    out = tmp_path / "brief.md"
    for _ in range(2):
        result = runner.invoke(app, ["report", str(tmp_path / "acme"), "--out", str(out),
                                     "--today", "2026-10-12"])
        assert result.exit_code == 0, result.output
    first = out.read_text()
    runner.invoke(app, ["report", str(tmp_path / "acme"), "--out", str(out),
                        "--today", "2026-10-12"])
    assert out.read_text() == first
    assert not (tmp_path / "acme" / "artifacts" / "REPORT.md").exists()


def test_the_brief_carries_the_contract_the_waivers_and_a_triggered_stop(tmp_path):
    start_engagement(tmp_path, "acme", statement=STATEMENT)
    eng = load_engagement(tmp_path / "acme")
    waived = runner.invoke(app, ["waive", str(eng.root), "client_readiness",
                                 "--reason", "the support lead is named and will grade",
                                 "--by", "Priya"])
    assert waived.exit_code == 0, waived.output
    contract = runner.invoke(app, ["outcome-contract", str(eng.root), "--owner", "Priya",
                                   "--metric", "time_to_first_reply", "--baseline", "26",
                                   "--unit", "h", "--target", "8", "--method", "ticket log",
                                   "--window", "30 days"])
    assert contract.exit_code == 0, contract.output
    project = tmp_path / "project"
    project.mkdir()
    (project / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "holds": True,
         "measured": "77.5% on 3036 cases (majority 1.9%; abstained 10.5%, 86.6% on the answered)"},
    ]}))
    (eng.root / ".last-out").write_text(str(project))
    record_conditions(eng, ["answered_accuracy < 0.88"], by="Priya", at="2026-09-21")
    result = runner.invoke(app, ["report", str(eng.root), "--today", "2026-10-12"])
    assert result.exit_code == 0, result.output
    text = (eng.root / "artifacts" / "REPORT.md").read_text()
    assert "- **owner**: Priya" in text and "- **target**: 8 h" in text
    assert "- **baseline**: 26 h" in text
    assert "### Gates waived" in text and "the support lead is named" in text
    assert "STOP  answered_accuracy < 0.88" in text and "0.866" in text


def test_the_brief_opens_with_five_statuses_none_implying_the_next(tmp_path):
    """A design decided is not a build; a build is not an implementation; a
    green exam is not an outcome. The strip says each on its own line."""
    start_engagement(tmp_path, "acme", statement=STATEMENT)
    eng = load_engagement(tmp_path / "acme")
    result = runner.invoke(app, ["report", str(eng.root), "--today", "2026-10-17"])
    assert result.exit_code == 0, result.output
    text = (eng.root / "artifacts" / "REPORT.md").read_text()
    glance = text[text.index("## At a glance"):text.index("## The problem as stated")]
    assert "- **decided**: " in glance and "undecided: " in glance
    assert "- **built**: not built" in glance
    assert "- **implemented**: not built" in glance
    assert "- **evaluated**: not scored" in glance
    assert "- **outcome**: none recorded: the business impact is not measured" in glance
    # A build on record with one scaffold left, a holdout row, and an outcome.
    project = tmp_path / "project"
    (project / "app" / "components").mkdir(parents=True)
    (project / "app" / "components" / "perception.py").write_text(
        "SCAFFOLD = True  # fde: the contract is decided, the body is not\n")
    (project / "app" / "components" / "representation.py").write_text("def run(p): return p\n")
    (project / "scorecard.json").write_text(json.dumps({"rows": [
        {"property": "holdout", "holds": True, "measured": "73.8% on 3036 cases"}]}))
    (eng.root / ".last-out").write_text(str(project))
    (eng.root / "outcomes.jsonl").write_text(
        json.dumps({"metric": "adoption", "value": 0.6}) + "\n")
    runner.invoke(app, ["report", str(eng.root), "--today", "2026-10-17"])
    text = (eng.root / "artifacts" / "REPORT.md").read_text()
    glance = text[text.index("## At a glance"):text.index("## The problem as stated")]
    assert f"- **built**: `{project}`" in glance
    assert "- **implemented**: 1 component(s) still scaffolds: perception" in glance
    assert "- **evaluated**: holdout 73.8% on 3036 cases (holds)" in glance
    assert "- **outcome**: 1 outcome(s) recorded" in glance
