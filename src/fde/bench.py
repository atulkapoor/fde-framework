"""A bench of engagements: the same figures read off every record, side
by side.

Nothing here is a benchmark of the field. It is what each engagement's
own record shows -- the stage last recorded, the holdout and external
figures on its card, the gap, incidents, days to pilot, rounds the loop
took -- so that engagements can be compared on what was measured rather
than on what was said about them. The table says how many rows it has;
four public demos are four rows, not a corpus.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fde.lifecycle import _jsonl, outcome_metrics
from fde.value import _card_numbers


def _card(project: Path | None) -> dict[str, dict] | None:
    if project is None or not (project / "scorecard.json").exists():
        return None
    try:
        return {r["property"]: r
                for r in json.loads((project / "scorecard.json").read_text()).get("rows", [])}
    except (ValueError, KeyError, TypeError):
        return None


def measure(engagement, project: Path | None) -> dict[str, Any]:
    root = Path(engagement.root)
    trail = _jsonl(root / "lifecycle.jsonl")
    card = _card(project)
    numbers = _card_numbers(card)
    external = gap = None
    verdict = None
    if card:
        match = re.search(r"([0-9.]+)% on (\d+) cases", card.get("external exam", {})
                          .get("measured", ""))
        if match:
            external = float(match.group(1)) / 100
        match = re.search(r"= ([+-]?[0-9.]+)%", card.get("generalisation gap", {})
                          .get("measured", ""))
        if match:
            gap = float(match.group(1)) / 100
        held = sum(1 for r in card.values() if r.get("holds") is True)
        measured = sum(1 for r in card.values() if r.get("holds") in (True, False))
        verdict = f"{held}/{measured}"
    metrics = outcome_metrics(engagement, project)
    return {
        "engagement": root.name,
        "stage": trail[-1]["stage"] if trail else "unrecorded",
        "card": verdict,
        "holdout": numbers["holdout"],
        "abstained": numbers["abstain_rate"],
        "answered_accuracy": numbers["answered_accuracy"],
        "holdout_cases": int(numbers["cases"]) if numbers["cases"] else None,
        "external": external,
        "gap": gap,
        "days_to_pilot": metrics["days_to_pilot"],
        "rounds": metrics["implement_rounds_logged"],
        "incidents": f"{metrics['incidents_opened']} opened, {metrics['incidents_open']} open",
        "value": (project / "VALUE.md").exists() if project else False,
        "outcomes": len(metrics["outcomes_recorded"]),
    }


def _pct(value: float | None) -> str:
    return "--" if value is None else f"{value:.1%}"


def _signed(value: float | None) -> str:
    return "--" if value is None else f"{value:+.1%}"


def render(rows: list[dict[str, Any]]) -> str:
    lines = ["# Bench", "",
             f"{len(rows)} engagement(s), each read off its own record: the stage last "
             "recorded by `fde stage`, the out-of-sample rows on its last scorecard, and "
             "what the trail shows. A row with `--` did not measure that property. This "
             "is the framework's record of these engagements, not a benchmark of the "
             "field.", "",
             "| Engagement | Stage | Card | Holdout | Abstained | On the answered | Cases | "
             "External | Gap | Days to pilot | Rounds | Incidents | Value | Outcomes |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['engagement']} | {r['stage']} | {r['card'] or '--'} | {_pct(r['holdout'])} | "
            f"{_pct(r['abstained'])} | {_pct(r['answered_accuracy'])} | "
            f"{r['holdout_cases'] or '--'} | {_pct(r['external'])} | "
            f"{_signed(r['gap'])} | "
            f"{'--' if r['days_to_pilot'] is None else r['days_to_pilot']} | {r['rounds']} | "
            f"{r['incidents']} | {'VALUE.md' if r['value'] else '--'} | {r['outcomes']} |")
    return "\n".join(lines) + "\n"
