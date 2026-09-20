"""The business-value engine: what the measured system is worth, in the
client's own figures, with every input labelled by where it came from.

An engagement is bought on a number nobody measured -- hours saved, a
payback period -- and the number is usually assembled after the fact from
whatever flatters it. This reads the recorded baseline (volume, cycle
time, labour, error rate) and the scorecard's out-of-sample rows (how much
the system answers, how often it is right when it does) and writes down
what follows: the automated share, the residual human work, the errors
the system would add or remove, hours and money per year, the cost to
build and run, payback. Each line says whether it rests on a measurement,
a stated figure, or an assumption the caller supplied, so the number can
be argued row by row rather than believed or dismissed whole.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

WORKING_WEEKS = 48


@dataclass
class Line:
    name: str
    value: Any
    unit: str
    basis: str  # measured | stated | assumed | derived
    note: str = ""


@dataclass
class Value:
    lines: list[Line] = field(default_factory=list)

    def get(self, name: str) -> Any:
        return next((line.value for line in self.lines if line.name == name), None)

    def add(self, name: str, value: Any, unit: str, basis: str, note: str = "") -> None:
        self.lines.append(Line(name, value, unit, basis, note))


def _figure(baseline: dict | None, key: str) -> tuple[float | None, str]:
    """(value, basis) for one baseline field: stated when its definition
    says so, measured otherwise, absent when missing."""
    if not baseline or key not in baseline:
        return None, "absent"
    entry = baseline[key]
    value = entry.get("value") if isinstance(entry, dict) else entry
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None, "absent"
    definition = entry.get("definition", "") if isinstance(entry, dict) else ""
    stated = bool(re.search(r"estimat|scenario|assum|guess|approx|\bstated\b|not measured|"
                            r"reported by|said\b", definition, re.I))
    return float(value), ("stated" if stated else "measured")


def _card_numbers(rows: dict[str, dict] | None) -> dict[str, float | None]:
    """The out-of-sample figures off a scorecard's rows."""
    out: dict[str, float | None] = {"holdout": None, "answered_accuracy": None,
                                    "abstain_rate": None, "cases": None}
    if not rows:
        return out
    measured = rows.get("holdout", {}).get("measured", "")
    match = re.search(r"([0-9.]+)% on (\d+) cases", measured)
    if match:
        out["holdout"] = float(match.group(1)) / 100
        out["cases"] = float(match.group(2))
    match = re.search(r"abstained ([0-9.]+)%, ([0-9.]+)% on the answered", measured)
    if match:
        out["abstain_rate"] = float(match.group(1)) / 100
        out["answered_accuracy"] = float(match.group(2)) / 100
    elif out["holdout"] is not None:
        out["abstain_rate"] = 0.0
        out["answered_accuracy"] = out["holdout"]
    return out


def estimate(baseline: dict | None, card_rows: dict[str, dict] | None, *,
             hourly_cost: float, implementation_hours: float, monthly_run_cost: float,
             review_share: float | None = None) -> Value:
    """The estimate. `review_share` is the share of automated decisions a
    person still checks (an assumption the caller states); None means
    the abstained share is the only human work left."""
    value = Value()
    volume, volume_basis = _figure(baseline, "volume")
    cycle, cycle_basis = _figure(baseline, "cycle_time_per_unit_seconds")
    labour, labour_basis = _figure(baseline, "labour_hours_per_week")
    error_rate, error_basis = _figure(baseline, "error_rate")
    numbers = _card_numbers(card_rows)

    if volume is None or cycle is None:
        value.add("estimate", None, "", "absent",
                  "no volume or cycle time on the baseline; nothing to value")
        return value

    entry = baseline.get("volume")
    unit = entry.get("unit", "items/month") if isinstance(entry, dict) else "items/month"
    per_period = 12 if "month" in unit else 52 if "week" in unit else 260 if "day" in unit else 1
    per_year = volume * per_period
    value.add("annual volume", round(per_year), "items/year", volume_basis, f"from {volume} {unit}")
    human_hours = per_year * cycle / 3600
    value.add("human hours today", round(human_hours), "hours/year", cycle_basis,
              f"{cycle:.0f} s per item, {volume_basis} cycle time")
    if labour is not None:
        value.add("labour on record", round(labour * WORKING_WEEKS), "hours/year", labour_basis,
                  f"{labour} h/week x {WORKING_WEEKS} weeks; the cycle-time figure above is "
                  f"the one used")
    value.add("hourly cost", hourly_cost, "per hour", "assumed", "supplied by the caller")
    value.add("cost of the work today", round(human_hours * hourly_cost), "per year", "derived")

    if numbers["holdout"] is None:
        value.add("automated share", None, "", "absent",
                  "no holdout row on the scorecard; run fde scorecard --holdout first")
        return value
    abstain = numbers["abstain_rate"] or 0.0
    accuracy = numbers["answered_accuracy"] or 0.0
    automated = 1 - abstain
    value.add("automated share", round(automated, 3), "of items", "measured",
              f"1 - the holdout's abstain rate ({abstain:.1%}) on {int(numbers['cases'])} "
              f"cases never shipped")
    value.add("accuracy on the automated", round(accuracy, 3), "", "measured",
              "the holdout's accuracy on what the system answered")
    review = review_share if review_share is not None else 0.0
    if review:
        value.add("human review of automated items", review, "share", "assumed",
                  "supplied by the caller: a person checks this share of automated decisions")
    residual = abstain + automated * review
    value.add("residual human share", round(residual, 3), "of items", "derived",
              "abstained items plus the reviewed share")
    hours_saved = human_hours * (1 - residual)
    value.add("hours saved", round(hours_saved), "hours/year", "derived")
    value.add("saving", round(hours_saved * hourly_cost), "per year", "derived")

    if error_rate is not None:
        added = per_year * automated * (1 - accuracy)
        removed = per_year * automated * error_rate
        value.add("errors the system makes on the automated", round(added), "items/year",
                  "measured", f"{1 - accuracy:.1%} of the automated items")
        value.add("errors a person made on the same items", round(removed), "items/year",
                  error_basis, f"{error_rate:.1%} first-pass error rate on the baseline")
        value.add("net errors", round(added - removed), "items/year", "derived",
                  "positive means the system adds errors; the cost of one is the client's "
                  "figure to supply")

    build = implementation_hours * hourly_cost
    run = monthly_run_cost * 12
    value.add("cost to build", round(build), "one-off", "assumed",
              f"{implementation_hours} hours at the hourly cost")
    value.add("cost to run", round(run), "per year", "assumed",
              f"{monthly_run_cost} per month, supplied by the caller")
    net = hours_saved * hourly_cost - run
    value.add("net benefit", round(net), "per year", "derived", "saving minus the cost to run")
    if net > 0:
        value.add("payback", round(build / net * 12, 1), "months", "derived")
    else:
        value.add("payback", None, "months", "derived", "the saving does not cover the cost to run")
    # A risk-adjusted view: the holdout's own uncertainty, Wilson 95% on the
    # answered accuracy, applied to the saving.
    n = (numbers["cases"] or 0) * automated
    if n > 0:
        z = 1.96
        centre = (accuracy + z * z / (2 * n)) / (1 + z * z / n)
        half = z * ((accuracy * (1 - accuracy) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
        value.add("accuracy interval", f"{max(0.0, centre - half):.1%} to "
                  f"{min(1.0, centre + half):.1%}", "95%", "derived",
                  f"Wilson interval on {int(n)} answered holdout cases")
    return value


def render(value: Value, engagement: str) -> str:
    lines = ["# Value", "",
             f"What the measured system is worth to `{engagement}`, in the client's own "
             "figures. Every line says what it rests on: **measured** by the exam or the "
             "baseline, **stated** by the client and not measured, **assumed** by the "
             "caller of this estimate, or **derived** from the lines above it. Argue the "
             "rows, not the total.", "",
             "| Line | Value | Unit | Basis | Note |", "|---|---|---|---|---|"]
    for line in value.lines:
        shown = "--" if line.value is None else line.value
        lines.append(f"| {line.name} | {shown} | {line.unit} | {line.basis} | {line.note} |")
    stated = [line.name for line in value.lines if line.basis == "stated"]
    assumed = [line.name for line in value.lines if line.basis == "assumed"]
    lines.append("")
    if stated:
        lines.append(f"Stated, not measured: {', '.join(stated)}. Measure these before "
                     "quoting the total.")
    if assumed:
        lines.append(f"Assumed by the caller: {', '.join(assumed)}.")
    return "\n".join(lines) + "\n"
