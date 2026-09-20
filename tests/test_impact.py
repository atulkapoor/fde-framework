"""fde next says what the answer would change: the evidence on record for
the dimension and the decisions that turn on each candidate answer."""

from __future__ import annotations

from typer.testing import CliRunner

from fde.cli import DEFAULT_ROOT, app
from fde.factlog import load_engagement, start_engagement
from fde.impact import decision_impact, render_impact
from fde.registry import load_registry
from fde.space import Space

runner = CliRunner()


def test_impact_tries_every_candidate_without_touching_the_record(tmp_path):
    start_engagement(tmp_path, "acme", statement="Answer staff questions from policy PDFs.")
    eng = load_engagement(tmp_path / "acme")
    registry = load_registry(DEFAULT_ROOT)
    space = Space.from_registry(registry).apply(eng.profile)
    open_dims = [d for d in space.dimensions() if not space.resolved(d)]
    assert open_dims, "the fixture must leave something to ask"
    before = eng.profile.values()
    impact = decision_impact(open_dims[0], eng.profile, registry, space)
    assert eng.profile.values() == before
    assert impact.explorable and len(impact.outcomes) >= 2
    text = render_impact(impact)
    assert "impact:" in text and "answer(s) explored" in text


def test_next_prints_the_impact_when_it_asks(tmp_path):
    start_engagement(tmp_path, "acme", statement="Answer staff questions from policy PDFs.")
    root = str(tmp_path / "acme")
    eng = load_engagement(tmp_path / "acme")
    # Clear every gate so the ladder reaches the interview rung.
    eng.record_data_access("rows", "2026-09-01")
    eng.record_security_review("reviewed", "2026-09-01")
    eng.record_baseline({
        "volume": {"value": 100, "unit": "q/day", "definition": "questions asked"},
        "cycle_time_per_unit_seconds": {"value": 600, "unit": "s",
                                        "definition": "measured on 40 questions"},
        "labour_hours_per_week": {"value": 20, "unit": "h", "definition": "counted"},
        "rework_rate": {"value": 0.1, "unit": "share", "definition": "re-asked"},
        "exception_rate": {"value": 0.05, "unit": "share", "definition": "escalated"},
        "error_rate": {"value": 0.08, "unit": "share", "definition": "wrong answers found"},
        "business_metric": {"value": 2, "unit": "days", "definition": "time to answer"},
        "sampled": {"n": 40, "method": "random week"},
    })
    eng.record_outcome_contract({"owner": "ops lead", "metric": "time_to_answer",
                                 "baseline": {"value": 2, "unit": "days"},
                                 "target": {"value": 0.5, "unit": "days"},
                                 "method": "ticket timestamps", "window": "60 days"})
    (eng.artifacts_dir / "pairs.jsonl").write_text(
        '{"id": "1", "input": "q", "output": "a", "verified": true}\n')
    for gate in ("client_readiness", "offline_evaluability", "licence_compatibility"):
        runner.invoke(app, ["waive", root, gate, "--reason", "test fixture, knowingly"])
    result = runner.invoke(app, ["next", root])
    assert result.exit_code == 0, result.output
    if result.output.startswith("next: fde ask"):
        assert "evidence on" in result.output and "impact:" in result.output
