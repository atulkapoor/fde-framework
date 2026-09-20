"""Stop conditions: what evidence would make this engagement stop.

An engagement that cannot say what would stop it cannot be stopped by
evidence, only by exhaustion. So the outcome contract carries stop
conditions -- `answered_accuracy < 0.88`, `abstain_rate > 0.35`,
`adoption < 0.4` -- over figures the record measures: the scorecard's
out-of-sample rows, the field journal, and the outcomes recorded in the
field. Each is evaluated against what was measured, never estimated; a
figure the record has not measured leaves its condition unjudged and
says so. One triggered condition makes STOP the engagement's stage, on
the record with the trigger and the threshold, until somebody restates
the condition with a reason, changes the build, or captures the case.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from fde.value import card_figures

CONDITION = re.compile(r"^\s*(?P<name>[a-z][a-z0-9_]*)\s*(?P<op>>=|<=|==|!=|>|<)\s*"
                       r"(?P<value>-?\d+(?:\.\d+)?)\s*$")
OPS = {">": lambda a, b: a > b, "<": lambda a, b: a < b, ">=": lambda a, b: a >= b,
       "<=": lambda a, b: a <= b, "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
CARD_FIGURES = ("holdout_accuracy", "answered_accuracy", "abstain_rate", "external_accuracy",
                "generalisation_gap")
FIELD_FIGURES = ("field_abstain_rate", "field_error_rate", "field_mix_distance")


class StopError(ValueError):
    """A condition that cannot be read."""


@dataclass
class Verdict:
    condition: str
    measured: float | None
    triggered: bool | None  # None: the figure is not on the record

    @property
    def name(self) -> str:
        return parse(self.condition)[0]


def parse(condition: str) -> tuple[str, str, float]:
    match = CONDITION.match(condition)
    if not match:
        raise StopError(f"{condition!r}: a stop condition is `<figure> <op> <number>`, e.g. "
                        "answered_accuracy < 0.88; figures are the scorecard's "
                        f"{', '.join(CARD_FIGURES)}, the field's {', '.join(FIELD_FIGURES)}, "
                        "or any metric recorded with fde outcome")
    return match.group("name"), match.group("op"), float(match.group("value"))


def figures(engagement, project: Path | None, journal: Path | None = None) -> dict[str, float]:
    """Every figure the record has measured, by name."""
    out: dict[str, float] = {}
    if project is not None and (project / "scorecard.json").exists():
        try:
            rows = {r["property"]: r
                    for r in json.loads((project / "scorecard.json").read_text()).get("rows", [])}
        except (ValueError, KeyError, TypeError):
            rows = None
        for name, value in card_figures(rows).items():
            if name in CARD_FIGURES and value is not None:
                out[name] = value
    if journal is not None and Path(journal).exists():
        from fde.drift import _distance, expectations, read_journal

        read = read_journal(Path(journal))
        if read.answered:
            out["field_abstain_rate"] = read.abstained / read.answered
        if read.requests:
            out["field_error_rate"] = read.errors / read.requests
        if project is not None:
            distance = _distance(read.decisions, expectations(project)["mix"])
            if distance is not None:
                out["field_mix_distance"] = distance
    outcomes = Path(engagement.root) / "outcomes.jsonl"
    if outcomes.exists():
        for line in outcomes.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            value = row.get("value")
            if isinstance(value, (int, float)) and not isinstance(value, bool) \
                    and isinstance(row.get("metric"), str):
                out[row["metric"]] = float(value)  # the latest line wins
    return out


def conditions(engagement) -> list[str]:
    contract = engagement.outcome_contract() if hasattr(engagement, "outcome_contract") \
        else None
    if not isinstance(contract, dict):
        return []
    raw = contract.get("stop_when") or []
    return [str(c) for c in raw if str(c).strip()]


def record(engagement, new: list[str], by: str = "", at: str | None = None) -> list[str]:
    """Append stop conditions to the outcome contract, each parsed first;
    a condition already on record is not written twice."""
    for condition in new:
        parse(condition)
    path = Path(engagement.root) / "outcome.yaml"
    contract = yaml.safe_load(path.read_text()) if path.exists() else None
    if not isinstance(contract, dict):
        contract = {}
    existing = [str(c) for c in contract.get("stop_when") or []]
    added = [c.strip() for c in new if c.strip() not in existing]
    contract["stop_when"] = existing + added
    contract.setdefault("stop_when_recorded", []).extend(
        {"condition": c, "at": at or date.today().isoformat(), **({"by": by} if by else {})}
        for c in added)
    path.write_text(yaml.safe_dump(contract, sort_keys=False))
    return added


def evaluate(conditions_: list[str], measured: dict[str, float]) -> list[Verdict]:
    verdicts = []
    for condition in conditions_:
        name, op, threshold = parse(condition)
        value = measured.get(name)
        verdicts.append(Verdict(condition, value,
                                None if value is None else OPS[op](value, threshold)))
    return verdicts


def triggered(verdicts: list[Verdict]) -> list[Verdict]:
    return [v for v in verdicts if v.triggered]


def render(verdicts: list[Verdict], measured: dict[str, Any]) -> str:
    if not verdicts:
        return ("no stop conditions on record: fde stop-when <eng> --when \"answered_accuracy "
                "< 0.88\"")
    lines = []
    for verdict in verdicts:
        if verdict.triggered is None:
            mark, shown = "  ?  ", "not measured on the record"
        elif verdict.triggered:
            mark, shown = "STOP ", f"measured {verdict.measured:.4g}"
        else:
            mark, shown = "  ok ", f"measured {verdict.measured:.4g}"
        lines.append(f"{mark} {verdict.condition:36} {shown}")
    fired = triggered(verdicts)
    if fired:
        lines += ["", f"STOP: {len(fired)} condition(s) triggered. The stage is stopped until "
                  "the condition is restated with a reason, the build is changed and scored "
                  "again, or the case is captured (fde retro)."]
    return "\n".join(lines)
