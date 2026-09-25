"""The engagement's history, in order: everything dated on the record,
one line each, and what the record holds without a date above it.

For whoever picks the engagement up -- a colleague, the same person after
a month away -- this is the page to read first. Nothing is summarised;
each line is one entry from one file, so any of them can be checked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from fde.lifecycle import _jsonl


def events(engagement) -> tuple[list[dict[str, Any]], list[str]]:
    """(dated events sorted by date, undated notes)."""
    root = Path(engagement.root)
    dated: list[dict[str, Any]] = []
    undated: list[str] = []

    def add(at: str | None, kind: str, what: str, by: str | None = None) -> None:
        if at:
            dated.append({"at": str(at), "kind": kind, "what": what, "by": by or ""})
        else:
            undated.append(f"{kind}: {what}")

    for statement in engagement.statements:
        text = statement.text.replace("\n", " ")
        what = (text[:90] + "...") if len(text) > 90 else text
        if statement.reason:
            what += f"  (revised: {statement.reason})"
        add(None, f"statement v{statement.version}", what)
    facts_dir = root / "facts"
    if facts_dir.is_dir():
        for path in sorted(facts_dir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError:
                continue
            respondent = raw.get("respondent") or {}
            who = respondent.get("name") or respondent.get("role", "?")
            add(None, f"session {path.stem}", f"{len(raw.get('facts') or [])} fact(s) from {who}")
    raw_state = engagement._raw_gate_state() if hasattr(engagement, "_raw_gate_state") else {}
    if isinstance(raw_state, dict):
        for key in ("data_access", "security_review", "deployed"):
            entry = raw_state.get(key)
            if isinstance(entry, dict) and entry.get("note"):
                add(entry.get("at"), key.replace("_", " "), str(entry["note"]), entry.get("by"))
        for waiver in raw_state.get("overrides") or []:
            if isinstance(waiver, dict) and waiver.get("gate"):
                add(waiver.get("at"), f"waived {waiver['gate']}", str(waiver.get("reason", "")),
                    waiver.get("by"))
    if (root / "baseline.yaml").exists():
        add(None, "baseline", "recorded (baseline.yaml)")
    for override in _jsonl(root / "overrides.jsonl"):
        add(override.get("at"), f"override {override.get('component')}",
            f"{override.get('recommended')} -> {override.get('chosen')}: "
            f"{override.get('because', '')}")
    predicted: dict[str, list[str]] = {}
    for prediction in _jsonl(root / "predictions.jsonl"):
        predicted.setdefault(str(prediction.get("predicted_at")), []).append(
            str(prediction.get("trigger")))
        if prediction.get("observed_at"):
            add(prediction.get("observed_at"), "observed", str(prediction.get("trigger")))
    for at, triggers in predicted.items():
        add(at if at != "None" else None, "predicted",
            f"{len(triggers)} trigger(s): {', '.join(triggers)}")
    for person in _jsonl(root / "stakeholders.jsonl"):
        add(person.get("at"), "stakeholder", f"{person.get('name')} ({person.get('role')})")
    for forecast in _jsonl(root / "forecasts.jsonl"):
        add(forecast.get("at"), "forecast", str(forecast.get("condition", ""))
            + ("  (after a card existed)" if forecast.get("after_scoring") else ""),
            forecast.get("by"))
    for scored in _jsonl(root / "forecast-scores.jsonl"):
        results = scored.get("results") or []
        held = sum(1 for r in results if r.get("held") is True)
        missed = sum(1 for r in results if r.get("held") is False)
        add(scored.get("at"), "forecasts scored", f"{held} held, {missed} missed of "
            f"{len(results)}")
    for step in _jsonl(root / "lifecycle.jsonl"):
        add(step.get("at"), "stage", f"{step.get('from') or 'start'} -> {step.get('stage')}")
    for incident in _jsonl(root / "incidents.jsonl"):
        add(incident.get("opened_at"), f"incident {incident.get('id')} opened",
            str(incident.get("kind", "")))
        if incident.get("closed_at"):
            add(incident.get("closed_at"), f"incident {incident.get('id')} closed",
                str(incident.get("closed_with", "")), incident.get("closed_by"))
    for outcome in _jsonl(root / "outcomes.jsonl"):
        add(outcome.get("at"), f"outcome {outcome.get('metric')}",
            f"{outcome.get('value')}  {outcome.get('note', '')}".rstrip(), outcome.get("by"))
    if (root / "case.json").exists():
        add(None, "retrospective", "case.json captured")
    dated.sort(key=lambda e: e["at"])
    return dated, undated


def render(engagement, name: str) -> str:
    dated, undated = events(engagement)
    lines = [f"{name}: history", ""]
    if undated:
        lines.append("on the record, undated:")
        lines += [f"  {note}" for note in undated]
        lines.append("")
    for event in dated:
        by = f"  [{event['by']}]" if event["by"] else ""
        lines.append(f"  {event['at']}  {event['kind']:28} {event['what']}{by}")
    if not dated:
        lines.append("  nothing dated yet")
    return "\n".join(lines)
