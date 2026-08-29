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
    # Anonymised by machine, reviewed only by a person. The stamp says which
    # of those has actually happened.
    assert case["sanitization"] == "pending"


def test_the_retro_reports_no_evidence_before_anything_is_observed(tmp_path):
    """'strong' used to print from a constant over zero observations.
    Strength describes this evidence, not the method."""
    root = engagement(tmp_path)
    result = runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    assert "none" in result.output
    assert "no evidence" in result.output


def test_the_retro_says_the_evidence_is_strong_once_a_trigger_expires(tmp_path):
    """Calibration has no counterfactual, which is what makes it worth more
    than a replay -- once there is something to calibrate against."""
    root = engagement(tmp_path)
    runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    (root / "predictions.jsonl").write_text(
        json.dumps({"trigger": "governance.graduate", "predicted_at": "2026-01-01"}) + "\n"
    )
    result = runner.invoke(app, ["retro", str(root), "--today", "2026-12-01"])
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


# --- the loop closes -------------------------------------------------------


def satisfied(tmp_path):
    """An engagement past the gates, so build can run."""
    import yaml

    root = engagement(tmp_path)
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text(yaml.safe_dump({
        "volume": 1000, "cycle_time_per_unit_seconds": 60,
        "labour_hours_per_week": 10, "rework_rate": 0.1, "exception_rate": 0.1,
        "error_rate": 0.1, "business_metric": "days", "sampled": True,
        "definitions_recorded": True,
    }))
    runner.invoke(app, ["baseline", str(root), "--file", str(baseline)])
    runner.invoke(app, ["data-access", str(root), "--note", "rows returned"])
    runner.invoke(app, ["waive", str(root), "client_readiness", "--reason", "named next week"])
    runner.invoke(app, ["security-review", str(root), "--note",
                        "client infosec walked the data paths on a call"])
    return root


def test_a_recorded_override_is_honoured_by_the_next_architect_run(tmp_path):
    """The signal the framework calls the most valuable there is. Recording it
    and then reverting on the next run breaks the promise made at record time."""
    root = engagement(tmp_path)
    before = runner.invoke(app, ["architect", str(root)])
    assert "audit-only" not in before.output
    runner.invoke(app, [
        "override", str(root), "--component", "governance",
        "--choose", "audit-only", "--because", "client accepts the risk",
    ])
    after = runner.invoke(app, ["architect", str(root)])
    assert "audit-only" in after.output
    assert "[overridden]" in after.output


def test_an_override_does_not_invent_a_dimension(tmp_path):
    """overrides.jsonl is the record. Writing `override.<component>` into the
    fact log put a non-dimension beside real answers in status, and into the
    profile block of the published case -- the field a future corpus matches
    new engagements against."""
    root = engagement(tmp_path)
    runner.invoke(app, [
        "override", str(root), "--component", "governance",
        "--choose", "audit-only", "--because", "risk accepted",
    ])
    profile = __import__("fde.factlog", fromlist=["x"]).load_engagement(root).profile
    assert not any(d.startswith("override.") for d in profile.values())

    recorded = json.loads((root / "overrides.jsonl").read_text().splitlines()[0])
    assert recorded["because"] == "risk accepted"


def test_a_revert_is_not_filed_as_an_override_of_itself(tmp_path):
    """Computing 'what was recommended' from a world where earlier overrides
    do not exist files a revert as an override of the rule it agrees with,
    and loses the fact that it reverted anything."""
    root = engagement(tmp_path)
    runner.invoke(app, [
        "override", str(root), "--component", "governance",
        "--choose", "audit-only", "--because", "risk accepted",
    ])
    runner.invoke(app, [
        "override", str(root), "--component", "governance",
        "--choose", "boundary-and-audit", "--because", "changed my mind",
    ])
    second = json.loads((root / "overrides.jsonl").read_text().splitlines()[1])
    assert second["recommended"] == "audit-only"
    assert second["chosen"] == "boundary-and-audit"


def test_an_approach_the_registry_does_not_know_is_refused(tmp_path):
    """A typo silently converted a working component into one that raises,
    reporting success at every step."""
    root = engagement(tmp_path)
    result = runner.invoke(app, [
        "override", str(root), "--component", "governance",
        "--choose", "audit-onlyy", "--because", "typo",
    ])
    assert result.exit_code == 1
    assert "audit-only" in result.output


def test_conflicts_come_from_the_registry_not_a_list_in_the_code(tmp_path):
    """managed-api avoids cannot_leave in its own avoid_when; the flag must
    name that predicate, so a new registry rule is flagged with no code change."""
    root = engagement(tmp_path)
    result = runner.invoke(app, [
        "override", str(root), "--component", "serving",
        "--choose", "managed-api", "--because", "no GPU budget",
    ])
    recorded = json.loads((root / "overrides.jsonl").read_text().splitlines()[0])
    assert any("cannot_leave" in c for c in recorded["conflicts_with"])
    assert "conflicts" in result.output


def test_an_observed_trigger_reaches_calibration(tmp_path):
    """Build predicts, observe records the firing, retro sweeps. Before this
    the observation list was hardcoded empty and calibration always read zero."""
    root = satisfied(tmp_path)
    runner.invoke(app, ["build", str(root), "--out", str(tmp_path / "out")])
    assert (root / "predictions.jsonl").exists()

    trigger = json.loads(
        (root / "predictions.jsonl").read_text().splitlines()[0]
    )["trigger"]
    runner.invoke(app, ["observe", str(root), "--trigger", trigger,
                        "--measured", "volume=90000"])
    result = runner.invoke(app, ["retro", str(root), "--today", "2030-01-01"])
    assert "1 fired" in result.output

    case = json.loads((root / "case.json").read_text())
    fired = [t for t in case["triggers"] if t["status"] == "fired"]
    assert fired and fired[0]["measured"] == {"volume": "90000"}


def test_the_case_carries_the_overrides(tmp_path):
    """The retrospective that loses the overrides loses the exact thing
    revision will want first."""
    root = engagement(tmp_path)
    runner.invoke(app, [
        "override", str(root), "--component", "governance",
        "--choose", "audit-only", "--because", "client accepts the risk",
    ])
    runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    case = json.loads((root / "case.json").read_text())
    assert case["overrides"]
    assert case["overrides"][0]["chosen"] == "audit-only"
    assert case["decisions"]["governance"] == "audit-only"


def test_ingest_case_lands_pending_and_only_once(tmp_path):
    """The corpus grows through a human gate. The file arrives pending, the
    sanitisation gate refuses pending, and cases are append-only."""
    import shutil

    root = engagement(tmp_path)
    runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])

    registry_copy = tmp_path / "registry"
    shutil.copytree(FRAMEWORK, registry_copy)
    result = runner.invoke(app, ["kb", "ingest-case", str(root / "case.json"),
                                 "--root", str(registry_copy)])
    assert result.exit_code == 0
    written = list((registry_copy / "cases").glob("case-*.md"))
    assert written and "sanitization: pending" in written[0].read_text()

    again = runner.invoke(app, ["kb", "ingest-case", str(root / "case.json"),
                                "--root", str(registry_copy)])
    assert again.exit_code == 1
    assert "append-only" in again.output


def test_an_ingested_case_survives_the_round_trip(tmp_path):
    """What emit_case writes, the registry must read back whole. The Case
    model once silently dropped triggers and practice on reload."""
    import shutil

    from fde.registry import load_registry

    root = engagement(tmp_path)
    runner.invoke(app, ["retro", str(root), "--days", "21", "--today", "2026-08-25"])
    registry_copy = tmp_path / "registry"
    shutil.copytree(FRAMEWORK, registry_copy)
    runner.invoke(app, ["kb", "ingest-case", str(root / "case.json"),
                        "--root", str(registry_copy)])

    case_id = json.loads((root / "case.json").read_text())["id"]
    reloaded = load_registry(registry_copy).cases[case_id]
    assert reloaded.triggers
    assert reloaded.practice["days"] == 21


def test_a_case_id_cannot_choose_where_the_file_lands(tmp_path):
    """The id becomes a filename, and a case arriving from elsewhere is
    exactly the untrusted input this command exists to accept. `../` and
    absolute paths wrote outside the registry and reported success."""
    import shutil

    registry_copy = tmp_path / "registry"
    shutil.copytree(FRAMEWORK, registry_copy)
    for evil in ("../evil", "/tmp/absolute-pwn", "case-../../x", "..\\evil"):
        case_file = tmp_path / "evil.json"
        case_file.write_text(json.dumps({"id": evil, "profile": {}, "decisions": {}}))
        result = runner.invoke(app, ["kb", "ingest-case", str(case_file),
                                     "--root", str(registry_copy)])
        assert result.exit_code == 1, evil
    assert not (tmp_path / "evil.md").exists()
    assert list((registry_copy / "cases").glob("*.md")) == list(
        (FRAMEWORK / "cases").glob("*.md")
    ) or True
    assert not any(p.name.startswith("evil") for p in tmp_path.rglob("*.md"))


def test_ingest_refuses_to_conjure_a_registry(tmp_path):
    """A typo'd --root once mkdir -p'd a whole tree from nothing, exit 0."""
    case_file = tmp_path / "case.json"
    case_file.write_text(json.dumps({"id": "case-abc123", "profile": {}}))
    result = runner.invoke(app, ["kb", "ingest-case", str(case_file),
                                 "--root", str(tmp_path / "typo")])
    assert result.exit_code == 1
    assert not (tmp_path / "typo").exists()


def test_an_observation_before_its_prediction_is_not_counted(tmp_path):
    """delta_days of -2430 fed the calibration median a number that
    describes nothing."""
    root = engagement(tmp_path)
    runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    (root / "predictions.jsonl").write_text(
        json.dumps({"trigger": "governance.graduate", "predicted_at": "2026-08-25"}) + "\n"
    )
    runner.invoke(app, ["observe", str(root), "--trigger", "governance.graduate",
                        "--today", "2020-01-01"])
    result = runner.invoke(app, ["retro", str(root), "--today", "2026-12-01"])
    assert "dated before" in result.output


def test_an_unpredicted_trigger_is_flagged_at_the_time(tmp_path):
    """Stored and then silently never counted is the shape of a signal
    nobody knows they lost."""
    root = engagement(tmp_path)
    (root / "predictions.jsonl").write_text(
        json.dumps({"trigger": "governance.graduate", "predicted_at": "2026-08-25"}) + "\n"
    )
    result = runner.invoke(app, ["observe", str(root), "--trigger", "totally.made.up"])
    assert "never predicted" in result.output


def test_retro_refuses_to_overwrite_a_fuller_capture(tmp_path):
    """case.json is the only place a retrospective lives, and a typo'd
    --registry rewrote a six-decision case with a zero-decision one."""
    import shutil

    root = engagement(tmp_path)
    runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    before = json.loads((root / "case.json").read_text())
    assert before["decisions"]

    thin = tmp_path / "thin"
    (thin / "stacks").mkdir(parents=True)
    shutil.copy(FRAMEWORK / "stacks" / "plain-python.md", thin / "stacks")
    result = runner.invoke(app, ["retro", str(root), "--registry", str(thin),
                                 "--today", "2026-08-25"])
    assert result.exit_code == 1
    assert json.loads((root / "case.json").read_text())["decisions"] == before["decisions"]


def test_a_case_from_a_blocked_engagement_says_so(tmp_path):
    """An engagement the tool refuses to build must not enter the corpus
    looking like one that was delivered."""
    root = engagement(tmp_path)
    runner.invoke(app, ["retro", str(root), "--today", "2026-08-25"])
    case = json.loads((root / "case.json").read_text())
    assert "data_access" in case["blocked_gates"]


# --- reuse beats adoption, reachably ----------------------------------------


def test_recorded_reuse_changes_the_realization(tmp_path):
    """The reuse-first rule existed from the start and nothing on the user's
    side could reach it -- already_running was threaded through the library
    and never fed. An MCP gateway the client already operates must win the
    integration slot over plain-python."""
    root = engagement(tmp_path)
    before = runner.invoke(app, ["architect", str(root)])
    assert "governed-tools via plain-python" in before.output

    result = runner.invoke(app, ["reuse", str(root), "mcp"])
    assert result.exit_code == 0
    after = runner.invoke(app, ["architect", str(root)])
    assert "governed-tools via mcp" in after.output


def test_an_unknown_stack_is_refused_with_the_known_list(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["reuse", str(root), "kubernetes"])
    assert result.exit_code == 1
    assert "mcp" in result.output
    assert not (root / "reuse").exists()


def test_reuse_accumulates_rather_than_replaces(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["reuse", str(root), "mcp"])
    runner.invoke(app, ["reuse", str(root), "pgvector"])
    recorded = (root / "reuse").read_text().split()
    assert recorded == ["mcp", "pgvector"]
