"""Forecasts: what the engagement expected before it measured.

A decision is made on evidence; whether the evidence was enough only shows
when the numbers come in. So a forecast goes on the record before the
score -- `holdout_accuracy >= 0.82`, `abstain_rate <= 0.2`,
`field_abstain_rate <= 0.22` -- in the same grammar as a stop condition,
over the same measured figures, with an optional confidence. Each one
records what was in hand when it was made: which figures the record had
already measured, and digests of the card and the profile. A forecast
about a figure already measured is kept and marked as such, per figure,
because a forecast made after the number is not a forecast. After the
score each is held, missed or unmeasured, with the signed error; where
enough carry a confidence, the held rate is set beside the mean
confidence, which is the beginning of a calibration and not yet one.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from fde.stop import OPS, figures, parse

CALIBRATION_FLOOR = 5


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


def _digest(path: Path | None) -> str | None:
    if path is None or not Path(path).exists():
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def _profile_digest(engagement) -> str | None:
    try:
        values = engagement.profile.values()
    except AttributeError:
        return None
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()[:16]


def forecasts(engagement) -> list[dict]:
    return _jsonl(Path(engagement.root) / "forecasts.jsonl")


def record(engagement, conditions: list[str], project: Path | None = None,
           journal: Path | None = None, by: str = "", at: str | None = None,
           confidence: float | None = None) -> list[dict]:
    """Append forecasts, each parsed first, each carrying what was in hand:
    the figures already measured, and the card's and profile's digests."""
    for condition in conditions:
        parse(condition)
    if confidence is not None and not 0.0 <= confidence <= 1.0:
        raise ValueError("a confidence is a share between 0 and 1")
    measured = figures(engagement, project, journal)
    evidence = {"card": _digest(Path(project) / "scorecard.json") if project else None,
                "profile": _profile_digest(engagement),
                "figures_measured": sorted(measured)}
    existing = {f.get("condition") for f in forecasts(engagement)}
    added = []
    with (Path(engagement.root) / "forecasts.jsonl").open("a") as handle:
        for condition in conditions:
            condition = condition.strip()
            if condition in existing:
                continue
            name = parse(condition)[0]
            entry: dict[str, Any] = {"condition": condition,
                                     "at": at or date.today().isoformat(),
                                     "already_measured": name in measured,
                                     "evidence": evidence}
            if confidence is not None:
                entry["confidence"] = confidence
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
            "already_measured": bool(entry.get("already_measured",
                                               entry.get("after_scoring", False))),
            "confidence": entry.get("confidence"),
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


def calibration(results: list[dict]) -> str:
    judged = [r for r in results if r["held"] is not None and r.get("confidence") is not None]
    if not judged:
        return ""
    if len(judged) < CALIBRATION_FLOOR:
        return (f"calibration needs at least {CALIBRATION_FLOOR} judged forecasts with a "
                f"confidence; {len(judged)} on record")
    held = sum(1 for r in judged if r["held"]) / len(judged)
    mean = sum(r["confidence"] for r in judged) / len(judged)
    return (f"held rate {held:.0%} against mean confidence {mean:.0%} over {len(judged)} "
            f"judged forecasts with a confidence")


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
        if r.get("confidence") is not None:
            shown += f"  at {r['confidence']:.0%} confidence"
        flag = "  [the figure was already on the record]" if r["already_measured"] else ""
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
    note = calibration(results)
    if note:
        lines.append(note)
    return "\n".join(lines)
