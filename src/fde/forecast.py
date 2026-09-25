"""Forecasts: what the engagement expected before it measured.

A decision is made on evidence; whether the evidence was enough only shows
when the numbers come in. So a forecast goes on the record before the
score -- `holdout_accuracy >= 0.82`, `abstain_rate <= 0.2`,
`field_abstain_rate <= 0.22` -- in the same grammar as a stop condition,
over the same measured figures. After the score, each forecast is held,
missed or unmeasured, with the signed error; a forecast written after a
card already existed is kept but marked, because a forecast made after
the number is not a forecast. Over enough engagements the errors say
which decisions the framework and its people systematically over- or
under-call; one engagement says only whether this one's expectations
were met.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fde.stop import OPS, figures, parse


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def forecasts(engagement) -> list[dict]:
    return _jsonl(Path(engagement.root) / "forecasts.jsonl")


def record(engagement, conditions: list[str], project: Path | None = None, by: str = "",
           at: str | None = None) -> list[dict]:
    """Append forecasts, each parsed first. A forecast made when the project
    already has a scorecard is marked `after_scoring`."""
    for condition in conditions:
        parse(condition)
    already = bool(project is not None and (Path(project) / "scorecard.json").exists())
    existing = {f.get("condition") for f in forecasts(engagement)}
    added = []
    with (Path(engagement.root) / "forecasts.jsonl").open("a") as handle:
        for condition in conditions:
            condition = condition.strip()
            if condition in existing:
                continue
            entry: dict[str, Any] = {"condition": condition,
                                     "at": at or date.today().isoformat(),
                                     "after_scoring": already}
            if by.strip():
                entry["by"] = by.strip()
            if project is not None:
                entry["project"] = str(project)
            handle.write(json.dumps(entry) + "\n")
            added.append(entry)
            existing.add(condition)
    return added


def evaluate(entries: list[dict], measured: dict[str, float]) -> list[dict]:
    results = []
    for entry in entries:
        name, op, threshold = parse(str(entry.get("condition", "")))
        value = measured.get(name)
        results.append({
            "condition": entry.get("condition"),
            "measured": value,
            "held": None if value is None else OPS[op](value, threshold),
            "error": None if value is None else round(value - threshold, 4),
            "after_scoring": bool(entry.get("after_scoring")),
            "by": entry.get("by", ""),
        })
    return results


def score(engagement, project: Path | None, journal: Path | None = None,
          at: str | None = None) -> list[dict]:
    """Judge every forecast against what the record measured and append
    the scoring to forecast-scores.jsonl."""
    results = evaluate(forecasts(engagement), figures(engagement, project, journal))
    if results:
        with (Path(engagement.root) / "forecast-scores.jsonl").open("a") as handle:
            handle.write(json.dumps({"at": at or date.today().isoformat(),
                                     "project": str(project) if project else None,
                                     "results": results}) + "\n")
    return results


def render(results: list[dict]) -> str:
    if not results:
        return ("no forecasts on record: fde predict <eng> --when \"holdout_accuracy >= 0.8\" "
                "before the score")
    lines = []
    for r in results:
        if r["held"] is None:
            mark, shown = "  ?  ", "not measured on the record"
        else:
            mark = "  ok " if r["held"] else "MISS "
            shown = f"measured {r['measured']:.4g} (error {r['error']:+.4g})"
        flag = "  [made after a card existed]" if r["after_scoring"] else ""
        lines.append(f"{mark} {r['condition']:36} {shown}{flag}")
    held = sum(1 for r in results if r["held"] is True)
    missed = sum(1 for r in results if r["held"] is False)
    unmeasured = sum(1 for r in results if r["held"] is None)
    errors = [r["error"] for r in results if r["error"] is not None]
    summary = (f"{len(results)} forecast(s): {held} held, {missed} missed, {unmeasured} not "
               f"measured")
    if errors:
        summary += f"; mean signed error {sum(errors) / len(errors):+.4g}"
    lines += ["", summary]
    return "\n".join(lines)
