"""The production loop: the service's own journal, read against the exam.

A deployed system writes one JSON line per request -- what it decided,
how sure it was, whether it abstained, what failed. Nobody reads those
lines until something goes wrong. This module reads them the way the
scorecard reads the holdout: the abstain rate against the holdout's, the
decision mix against the golden set's, the error rate against zero, the
margin against what the exam saw -- and when the field has moved past a
threshold it opens an incident on the engagement record, with the
evidence and the move that follows (score the holdout again; if it fell,
the exam has drifted too, and the pairs need a fresh draw).

An open incident pulls the engagement's stage back to pilot until it is
closed by name. Silence is not health; a journal with no answered events
is reported as such.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

# Past these the field is not the exam any more.
ABSTAIN_MULTIPLIER = 2.0     # abstaining twice as often as on the holdout
MIX_DISTANCE = 0.25          # total variation distance between decision mixes
ERROR_RATE = 0.05            # errors over answered
MIN_EVENTS = 30              # fewer than this is a sample of nothing


@dataclass
class Journal:
    requests: int = 0
    answered: int = 0
    errors: int = 0
    abstained: int = 0
    decisions: Counter = field(default_factory=Counter)
    margins: list[float] = field(default_factory=list)
    refusals: int = 0


def read_journal(path: Path) -> Journal:
    journal = Journal()
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("event") == "answered":
            journal.requests += 1
            journal.answered += 1
            decision = event.get("decision")
            if event.get("decided_by") == "abstained" or decision == "unknown":
                journal.abstained += 1
            elif isinstance(decision, str):
                journal.decisions[decision] += 1
            margin = event.get("margin")
            if isinstance(margin, (int, float)):
                journal.margins.append(float(margin))
        elif event.get("level") == "error" and event.get("error"):
            journal.requests += 1
            journal.errors += 1
        elif event.get("event") in ("refused",) or event.get("refused"):
            journal.requests += 1
            journal.refusals += 1
    return journal


def expectations(project: Path) -> dict[str, Any]:
    """What the exam says the field should look like: the golden decision
    mix and the holdout's abstain rate from the last scorecard."""
    expected: dict[str, Any] = {"mix": Counter(), "abstain_rate": None}
    golden = project / "evals" / "golden.jsonl"
    if golden.exists():
        for line in golden.read_text().splitlines():
            if line.strip():
                output = json.loads(line).get("output")
                if isinstance(output, dict) and len(output) == 1:
                    output = next(iter(output.values()))
                if isinstance(output, str):
                    expected["mix"][output] += 1
    card = project / "scorecard.json"
    if card.exists():
        try:
            rows = {r["property"]: r for r in json.loads(card.read_text()).get("rows", [])}
            measured = rows.get("holdout", {}).get("measured", "")
            match = re.search(r"abstained ([0-9.]+)%", measured)
            if match:
                expected["abstain_rate"] = float(match.group(1)) / 100
        except (ValueError, KeyError, TypeError):
            pass
    return expected


def _distance(observed: Counter, expected: Counter) -> float | None:
    if not observed or not expected:
        return None
    labels = set(observed) | set(expected)
    total_o = sum(observed.values())
    total_e = sum(expected.values())
    return 0.5 * sum(abs(observed[k] / total_o - expected[k] / total_e) for k in labels)


@dataclass
class Finding:
    kind: str
    measured: str
    expected: str
    drifted: bool


@dataclass
class Drift:
    journal: Journal
    findings: list[Finding]

    @property
    def drifted(self) -> list[Finding]:
        return [f for f in self.findings if f.drifted]


def detect(journal: Journal, expected: dict[str, Any]) -> Drift:
    findings: list[Finding] = []
    if journal.answered < MIN_EVENTS:
        findings.append(Finding("sample", f"{journal.answered} answered events",
                                f"at least {MIN_EVENTS}", False))
        return Drift(journal, findings)
    error_rate = journal.errors / max(1, journal.requests)
    findings.append(Finding("errors", f"{error_rate:.1%} of {journal.requests} requests",
                            f"under {ERROR_RATE:.0%}", error_rate > ERROR_RATE))
    abstain_rate = journal.abstained / max(1, journal.answered)
    base = expected.get("abstain_rate")
    if base is not None:
        findings.append(Finding("abstention", f"{abstain_rate:.1%} of answered",
                                f"{base:.1%} on the holdout (drift past "
                                f"{ABSTAIN_MULTIPLIER:.0f}x)",
                                abstain_rate > max(0.02, base * ABSTAIN_MULTIPLIER)))
    distance = _distance(journal.decisions, expected.get("mix") or Counter())
    if distance is not None:
        top = ", ".join(f"{k} {v / max(1, sum(journal.decisions.values())):.0%}"
                        for k, v in journal.decisions.most_common(3))
        findings.append(Finding("decision mix", f"distance {distance:.2f} from the golden mix "
                                f"({top})", f"under {MIX_DISTANCE}", distance > MIX_DISTANCE))
    if journal.margins:
        ordered = sorted(journal.margins)
        p50 = ordered[len(ordered) // 2]
        findings.append(Finding("margin", f"median {p50:.2f} nats", "reported", False))
    return Drift(journal, findings)


def open_incident(engagement, drift: Drift, journal_path: Path, today: str | None = None) -> dict:
    root = Path(engagement.root)
    existing = [line for line in (root / "incidents.jsonl").read_text().splitlines()
                if line.strip()] if (root / "incidents.jsonl").exists() else []
    incident = {
        "id": f"inc-{len(existing) + 1:03d}",
        "status": "open",
        "opened_at": today or date.today().isoformat(),
        "kind": "drift: " + ", ".join(f.kind for f in drift.drifted),
        "journal": str(journal_path),
        "evidence": [{"kind": f.kind, "measured": f.measured, "expected": f.expected}
                     for f in drift.drifted],
        "next": "score the holdout again (fde scorecard <project> --holdout ...); if it fell, "
                "the exam has drifted with the field -- draw fresh pairs, rebuild, and close "
                "this incident by name (fde incident <eng> close <id> --note ...)",
    }
    with (root / "incidents.jsonl").open("a") as handle:
        handle.write(json.dumps(incident) + "\n")
    return incident


def close_incident(engagement, incident_id: str, note: str, today: str | None = None) -> bool:
    root = Path(engagement.root)
    path = root / "incidents.jsonl"
    if not path.exists():
        return False
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    found = False
    for row in rows:
        if row.get("id") == incident_id and row.get("status") == "open":
            row["status"] = "closed"
            row["closed_at"] = today or date.today().isoformat()
            row["closed_with"] = note
            found = True
    if found:
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return found


def render(drift: Drift) -> str:
    lines = [f"journal: {drift.journal.requests} requests, {drift.journal.answered} answered, "
             f"{drift.journal.errors} errors, {drift.journal.abstained} abstained", ""]
    for finding in drift.findings:
        mark = "DRIFT" if finding.drifted else "  ok "
        lines.append(f"  {mark} {finding.kind:14} {finding.measured}  "
                     f"(expected {finding.expected})")
    return "\n".join(lines)
