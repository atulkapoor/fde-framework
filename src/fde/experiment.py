"""The experiment as an instrument.

EXPERIMENT.md says how the thesis would be tested: two arms, what is
frozen before anything is built, what is measured, a blind review, and
what a given count can show. A protocol on paper is followed
approximately; one the record runs is followed exactly. So `start`
assigns the arm by a seeded draw balanced within the shape, records the
engineer, the order and a difficulty vector read off the profile, and
freezes what was on the record before the build: forecasts, the outcome
contract, the stop conditions. `close` reads the measures off the
record -- or off the control arm's log, kept in a template the same code
reads -- and lists what is missing rather than estimating it. `packet`
renders the blind-review packet in one plain form for both arms;
`review` records the reviewer's fixed form and their guess at the arm;
`report` sets paired differences across the series beside the blinding
accuracy and says which rung of evidence the count has reached.
"""

from __future__ import annotations

import json
import random
import secrets
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ARMS = ("with", "without")
PRIMARY_ENDPOINT = "blind-review architecture quality (mean of the six scores)"
DIFFICULTY_DIMENSIONS = ("output_shape", "input_format", "labelled_count", "corpus_size",
                         "external_systems", "hosting", "data_residency", "human_waiting",
                         "sensitivity_present", "arrival_rate")
REVIEW_FORM = ("evidence_sufficiency", "necessity", "operational_complexity",
               "implementation_complexity", "risk", "reversibility")
GUESSES = ("with", "without", "uncertain")
MATURITY = ((20, "stronger, and still observational unless assignment was controlled"),
            (10, "exploratory and worth reporting, with the spread"),
            (5, "paired and exploratory: reversals, stops and forecast errors can be compared"),
            (0, "descriptive only: the numbers describe these engagements, not the framework"))
CONTROL_LOG = "log.yaml"
PACKET_VERSION = 1  # bump when the packet's form changes; blinding is reported per version
FLOOR = 3  # a review score below this is reported on its own, whatever the mean says


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except ValueError:
        return None


def series_path(engagement) -> Path:
    return Path(engagement.root).parent / "experiment-series.json"


def load_series(path: Path) -> dict[str, Any]:
    series = _read_json(path) or {}
    series.setdefault("seed", secrets.randbelow(2**31))
    series.setdefault("engagements", [])
    return series


def maturity(n: int) -> str:
    for floor, words in MATURITY:
        if n >= floor:
            return words
    return MATURITY[-1][1]


def difficulty(engagement) -> dict[str, Any]:
    """What can be read off the profile before anything is built, so
    engagements can be matched on it rather than on a feeling."""
    from fde.stakeholders import _sessions
    from fde.value import _figure

    profile = engagement.profile
    out: dict[str, Any] = {}
    for dimension in DIFFICULTY_DIMENSIONS:
        if profile.resolved(dimension):
            value = profile.get(dimension)
            out[dimension] = list(value) if isinstance(value, tuple) else value
    heard = _sessions(engagement)
    out["roles_heard"] = sorted(r for r in heard if r and r != "system")
    out["facts"] = sum(v["facts"] for v in heard.values())
    baseline = engagement.baseline()
    out["baseline"] = _figure(baseline, "cycle_time_per_unit_seconds")[1] if baseline else "none"
    return out


def assign(series: dict[str, Any], shape: str, order: int,
           forced: str | None = None) -> tuple[str, str]:
    """The arm, balanced within the shape: the lesser arm when the counts
    differ, a seeded draw when they are equal, the caller's when forced."""
    if forced:
        if forced not in ARMS:
            raise ValueError(f"arm is one of {', '.join(ARMS)}")
        return forced, "by hand"
    counts = Counter(e["arm"] for e in series["engagements"] if e.get("shape") == shape)
    if counts["with"] != counts["without"]:
        return ("with" if counts["with"] < counts["without"] else "without"), "balancing the shape"
    draw = random.Random(f"{series['seed']}:{shape}:{order}").choice(ARMS)
    return draw, f"seeded draw ({series['seed']}:{shape}:{order})"


def start(engagement, engineer: str, project: Path | None = None, series: Path | None = None,
          arm: str | None = None, at: str | None = None) -> dict[str, Any]:
    from fde.forecast import forecasts
    from fde.stop import conditions

    root = Path(engagement.root)
    if (root / "experiment.json").exists():
        raise FileExistsError("this engagement is already in the experiment")
    path = series or series_path(engagement)
    record = load_series(path)
    shape = str(engagement.profile.get("output_shape") or "unknown")
    order = len(record["engagements"]) + 1
    chosen, how = assign(record, shape, order, arm)
    entry = {
        "id": f"exp-{secrets.token_hex(4)}",
        "engagement": root.name, "engineer": engineer.strip(), "arm": chosen,
        "assigned": how, "shape": shape, "order": order,
        "started_at": at or date.today().isoformat(),
        "primary_endpoint": PRIMARY_ENDPOINT,
        "difficulty": difficulty(engagement),
        "frozen": {
            "forecasts": [f.get("condition") for f in forecasts(engagement)],
            "outcome_contract": engagement.outcome_contract(),
            "stop_when": conditions(engagement),
        },
        "built_already": bool(project and (Path(project) / "evals" / "manifest.json").exists()),
        "series": str(path),
    }
    (root / "experiment.json").write_text(json.dumps(entry, indent=2) + "\n")
    record["engagements"].append({"engagement": root.name, "shape": shape, "arm": chosen,
                                  "order": order, "id": entry["id"]})
    path.write_text(json.dumps(record, indent=2) + "\n")
    if chosen == "without" and not (root / CONTROL_LOG).exists():
        (root / CONTROL_LOG).write_text(control_template())
    return entry


def control_template() -> str:
    return """\
# The control arm's log: the same fields the framework's record supplies,
# kept by hand as the work happens, never reconstructed. Dates are
# YYYY-MM-DD. Leave a field empty rather than guess it; the close step
# lists what is missing.
statement: ""
evidence:            # one line each: what was known before building, and its basis
  - {what: "", basis: measured}   # measured | stated | assumed
outcome_contract: {owner: "", metric: "", baseline: null, target: null, method: "", window: ""}
decision: {chosen: "", rejected: [{approach: "", why: ""}]}
forecasts:           # written before the first line of implementation
  - {condition: "", confidence: null}
stop_when: []
dates: {scoped: "", architecture: "", first_build: "", green: "", pilot: ""}
hours: null          # engineer hours, from the timesheet
rounds: null         # implementation rounds to green
questions_asked: null
questions_that_changed_the_design: null
reversals: null      # architecture reversals after the first build
late_requirements: null
security_findings_after_design: null
fitness:
  {holdout_accuracy: null, coverage: null, external_accuracy: null,
   generalisation_gap: null, holdout_cases: null}
forecast_errors: []  # signed, one per forecast, once measured
outcome: {metric: "", measured: null, at: ""}
stopped_by: ""
"""


def _days(a: str | None, b: str | None) -> int | None:
    try:
        return (date.fromisoformat(str(b)) - date.fromisoformat(str(a))).days
    except (TypeError, ValueError):
        return None


def measures_with(engagement, project: Path | None, journal: Path | None) -> dict[str, Any]:
    from fde.forecast import evaluate, forecasts
    from fde.lifecycle import outcome_metrics
    from fde.stakeholders import _sessions
    from fde.stop import conditions, figures, triggered
    from fde.stop import evaluate as judge
    from fde.value import card_figures

    metrics = outcome_metrics(engagement, project)
    card = None
    if project and (Path(project) / "scorecard.json").exists():
        try:
            card = {r["property"]: r for r in json.loads(
                (Path(project) / "scorecard.json").read_text()).get("rows", [])}
        except (ValueError, KeyError, TypeError):
            card = None
    fit = card_figures(card)
    measured = figures(engagement, project, journal)
    scored = evaluate(forecasts(engagement), measured)
    errors = [r["error"] for r in scored if r["error"] is not None]
    heard = _sessions(engagement)
    stopped = triggered(judge(conditions(engagement), measured))
    return {
        "days_to_pilot": metrics["days_to_pilot"],
        "rounds": metrics["implement_rounds_logged"],
        "reversals": metrics["architecture_reversals"],
        "incidents": metrics["incidents_opened"],
        "questions_asked": sum(v["facts"] for r, v in heard.items() if r != "system"),
        "holdout_accuracy": fit["holdout_accuracy"],
        "coverage": None if fit["abstain_rate"] is None else round(1 - fit["abstain_rate"], 4),
        "external_accuracy": fit["external_accuracy"],
        "generalisation_gap": fit["generalisation_gap"],
        "forecasts_scored": len([r for r in scored if r["held"] is not None]),
        "forecast_mean_error": round(sum(errors) / len(errors), 4) if errors else None,
        "stopped_by": "; ".join(v.condition for v in stopped) or "",
        "hours": None,
        "late_requirements": None,
        "security_findings_after_design": None,
    }


def measures_without(engagement) -> dict[str, Any]:
    log = yaml.safe_load((Path(engagement.root) / CONTROL_LOG).read_text()) or {}
    dates = log.get("dates") or {}
    fit = log.get("fitness") or {}
    errors = [e for e in (log.get("forecast_errors") or []) if isinstance(e, (int, float))]
    return {
        "days_to_pilot": _days(dates.get("scoped"), dates.get("pilot")),
        "rounds": log.get("rounds"),
        "reversals": log.get("reversals"),
        "incidents": None,
        "questions_asked": log.get("questions_asked"),
        "holdout_accuracy": fit.get("holdout_accuracy"),
        "coverage": fit.get("coverage"),
        "external_accuracy": fit.get("external_accuracy"),
        "generalisation_gap": fit.get("generalisation_gap"),
        "forecasts_scored": len(errors),
        "forecast_mean_error": round(sum(errors) / len(errors), 4) if errors else None,
        "stopped_by": str(log.get("stopped_by") or ""),
        "hours": log.get("hours"),
        "late_requirements": log.get("late_requirements"),
        "security_findings_after_design": log.get("security_findings_after_design"),
    }


def close(engagement, project: Path | None = None, journal: Path | None = None,
          at: str | None = None) -> dict[str, Any]:
    root = Path(engagement.root)
    entry = _read_json(root / "experiment.json")
    if not entry:
        raise FileNotFoundError("not in the experiment: fde experiment <eng> start first")
    measures = (measures_with(engagement, project, journal) if entry["arm"] == "with"
                else measures_without(engagement))
    missing = sorted(k for k, v in measures.items() if v is None or v == "")
    closing = {"closed_at": at or date.today().isoformat(), "arm": entry["arm"],
               "measures": measures, "missing": missing}
    (root / "experiment-close.json").write_text(json.dumps(closing, indent=2) + "\n")
    return closing


def packet(engagement, project: Path | None = None, registry=None) -> str:
    """The blind-review packet, in one plain form for both arms and with
    no word in it that names the arm."""
    root = Path(engagement.root)
    entry = _read_json(root / "experiment.json") or {}
    lines = ["# Engagement packet", "", f"packet form v{PACKET_VERSION}", ""]
    if entry.get("arm") == "without" and (root / CONTROL_LOG).exists():
        log = yaml.safe_load((root / CONTROL_LOG).read_text()) or {}
        lines += ["## Problem", "", str(log.get("statement") or ""), "", "## Evidence in hand", ""]
        for item in log.get("evidence") or []:
            if isinstance(item, dict) and item.get("what"):
                lines.append(f"- {item['what']} [{item.get('basis', '?')}]")
        contract = log.get("outcome_contract") or {}
        decision = log.get("decision") or {}
        fit = log.get("fitness") or {}
        rejected = [(r.get("approach"), r.get("why")) for r in decision.get("rejected") or []
                    if isinstance(r, dict)]
        chosen = [("the system", decision.get("chosen"))]
    else:
        statement = engagement.current_statement()
        lines += ["## Problem", "", statement.text if statement else "", "",
                  "## Evidence in hand", ""]
        profile = engagement.profile
        for dimension in profile.dimensions():
            fact = profile.fact(dimension)
            if fact is not None:
                lines.append(f"- {dimension} = {fact.value} [{fact.provenance.value}]")
        contract = engagement.outcome_contract() or {}
        rejected, chosen, fit = [], [], {}
        if registry is not None:
            from fde.architect import architect as build_architecture
            architecture = build_architecture(profile, registry)
            for component, decision in architecture.decisions.items():
                chosen.append((component, decision.approach or "undecided"))
                rejected += [(f"{component}: {r.id}", r.reason) for r in decision.rejected]
        if project and (Path(project) / "scorecard.json").exists():
            from fde.value import card_figures
            try:
                rows = {r["property"]: r for r in json.loads(
                    (Path(project) / "scorecard.json").read_text()).get("rows", [])}
                figures = card_figures(rows)
                fit = {"holdout_accuracy": figures["holdout_accuracy"],
                       "coverage": (None if figures["abstain_rate"] is None
                                    else 1 - figures["abstain_rate"]),
                       "external_accuracy": figures["external_accuracy"],
                       "generalisation_gap": figures["generalisation_gap"],
                       "holdout_cases": figures["holdout_cases"]}
            except (ValueError, KeyError, TypeError):
                fit = {}
    lines += ["", "## Outcome contract", ""]
    for key in ("owner", "metric", "baseline", "target", "method", "window"):
        if contract.get(key) not in (None, ""):
            lines.append(f"- {key}: {contract[key]}")
    lines += ["", "## Architecture", ""]
    lines += [f"- {component}: {approach}" for component, approach in chosen]
    if rejected:
        lines += ["", "Rejected:", ""] + [f"- {name}: {why}" for name, why in rejected]
    lines += ["", "## Fitness", ""]
    lines += [f"- {k}: {v}" for k, v in fit.items() if v is not None] or ["- not measured"]
    text = "\n".join(lines) + "\n"
    (root / "experiment-packet.md").write_text(text)
    return text


def review(engagement, reviewer: str, scores: dict[str, int], contract_signable: bool,
           question_missed: str, guess: str, at: str | None = None) -> dict[str, Any]:
    for name in REVIEW_FORM:
        value = scores.get(name)
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"{name} is a whole number from 1 to 5")
    if guess not in GUESSES:
        raise ValueError(f"the guess is one of {', '.join(GUESSES)}")
    if not reviewer.strip():
        raise ValueError("the reviewer signs the form")
    form = {"reviewer": reviewer.strip(), "at": at or date.today().isoformat(),
            "packet_version": _packet_version(Path(engagement.root)),
            "scores": {name: scores[name] for name in REVIEW_FORM},
            "quality": round(sum(scores[name] for name in REVIEW_FORM) / len(REVIEW_FORM), 3),
            "contract_signable": bool(contract_signable),
            "question_missed": question_missed.strip(), "arm_guess": guess}
    (Path(engagement.root) / "experiment-review.json").write_text(
        json.dumps(form, indent=2) + "\n")
    return form


SECONDARIES = ("days_to_pilot", "hours", "rounds", "reversals", "holdout_accuracy", "coverage",
               "external_accuracy", "forecast_mean_error", "late_requirements")


def _packet_version(root: Path) -> int:
    packet_file = root / "experiment-packet.md"
    if packet_file.exists():
        for line in packet_file.read_text().splitlines():
            if line.startswith("packet form v"):
                try:
                    return int(line.split("v", 1)[1])
                except ValueError:
                    break
    return PACKET_VERSION


def withdraw(engagement, reason: str, at: str | None = None) -> dict[str, Any]:
    """An engagement leaves the series with its arm and a reason on the
    record. It stays in the series file: a withdrawal after the draw is
    the thing the report counts, by arm, because a lopsided count is what
    choosing engagements after seeing the arm looks like."""
    root = Path(engagement.root)
    entry = _read_json(root / "experiment.json")
    if not entry:
        raise FileNotFoundError("not in the experiment: nothing to withdraw")
    if not reason.strip():
        raise ValueError("a withdrawal needs a reason")
    record = {"at": at or date.today().isoformat(), "arm": entry["arm"],
              "reason": reason.strip()}
    (root / "experiment-withdrawn.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def difficulty_distance(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    """How unlike two frozen difficulty vectors are, 0 to 1: a decade apart
    on a count is 1, a different category is 1, a missing side is 1, a
    list is its Jaccard distance; the mean over every key either has."""
    import math

    keys = set(a) | set(b)
    parts = []
    for key in keys:
        x, y = a.get(key), b.get(key)
        if x is None and y is None:
            continue
        if x is None or y is None:
            parts.append(1.0)
        elif isinstance(x, bool) or isinstance(y, bool):
            parts.append(0.0 if x == y else 1.0)
        elif isinstance(x, (int, float)) and isinstance(y, (int, float)):
            parts.append(min(1.0, abs(math.log10((abs(x) + 1) / (abs(y) + 1)))))
        elif isinstance(x, list) and isinstance(y, list):
            sx, sy = set(map(str, x)), set(map(str, y))
            parts.append(1.0 - (len(sx & sy) / len(sx | sy) if sx | sy else 1.0))
        else:
            parts.append(0.0 if str(x) == str(y) else 1.0)
    return round(sum(parts) / len(parts), 3) if parts else None


def pair(withs: list[dict], withouts: list[dict]) -> list[tuple[dict, dict, float | None]]:
    """Within a shape, each *with* engagement to the unmatched *without*
    whose frozen difficulty is nearest, in series order; the distance is
    kept beside the pair so a bad match is visible."""
    free = list(withouts)
    pairs = []
    for a in withs:
        if not free:
            break
        scored = [(difficulty_distance(a.get("difficulty") or {}, b.get("difficulty") or {}), b)
                  for b in free]
        distance, b = min(scored, key=lambda s: (1.0 if s[0] is None else s[0],
                                                 s[1].get("order", 0)))
        pairs.append((a, b, distance))
        free.remove(b)
    return pairs


def _quality(row: dict) -> float | None:
    return (row.get("review") or {}).get("quality")


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def gather(series_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(Path(series_dir).glob("*/experiment.json")):
        entry = _read_json(path) or {}
        root = path.parent
        entry["close"] = _read_json(root / "experiment-close.json")
        entry["review"] = _read_json(root / "experiment-review.json")
        entry["withdrawn"] = _read_json(root / "experiment-withdrawn.json")
        rows.append(entry)
    return sorted(rows, key=lambda e: e.get("order", 0))


def report(series_dir: Path) -> str:
    rows = gather(series_dir)
    withdrawn = [r for r in rows if r.get("withdrawn")]
    active = [r for r in rows if not r.get("withdrawn")]
    n = len(active)
    lines = [f"experiment: {n} engagement(s) in {series_dir}"
             + (f", {len(withdrawn)} withdrawn" if withdrawn else ""),
             f"  evidence: {maturity(n)}",
             f"  primary endpoint: {PRIMARY_ENDPOINT}", ""]
    if withdrawn:
        by_arm = Counter(r["withdrawn"]["arm"] for r in withdrawn)
        lines.append(f"  withdrawn after the draw: with {by_arm['with']}, without "
                     f"{by_arm['without']} -- a lopsided count is what choosing engagements "
                     f"after seeing the arm looks like")
        lines += [f"    {r['engagement']} ({r['withdrawn']['arm']}): {r['withdrawn']['reason']}"
                  for r in withdrawn]
        lines.append("")
    if not active:
        return "\n".join(lines)
    by_shape: dict[str, dict[str, list]] = defaultdict(lambda: {"with": [], "without": []})
    for row in active:
        by_shape[row.get("shape", "?")][row["arm"]].append(row)
    pairs = 0
    unpaired: list[str] = []
    for shape, arms in sorted(by_shape.items()):
        lines.append(f"  {shape}: {len(arms['with'])} with, {len(arms['without'])} without")
        matched = pair(arms["with"], arms["without"])
        taken = {id(b) for _, b, _ in matched} | {id(a) for a, _, _ in matched}
        unpaired += [r["engagement"] for r in arms["with"] + arms["without"]
                     if id(r) not in taken]
        for a, b, distance in matched:
            pairs += 1
            qa, qb = _quality(a), _quality(b)
            primary = (f"{qa - qb:+.2f}" if qa is not None and qb is not None
                       else "missing a review")
            shown = "unmeasured" if distance is None else f"{distance:.2f}"
            lines.append(f"    pair {a['engagement']} / {b['engagement']} (orders "
                         f"{a.get('order')}/{b.get('order')}, difficulty distance {shown}): "
                         f"quality {primary}")
            ma = (a.get("close") or {}).get("measures") or {}
            mb = (b.get("close") or {}).get("measures") or {}
            for key in SECONDARIES:
                va, vb = ma.get(key), mb.get(key)
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    lines.append(f"      {key:22} {va - vb:+.4g}")
            if ma.get("stopped_by") or mb.get("stopped_by"):
                lines.append(f"      stopped: with={ma.get('stopped_by') or '-'} "
                             f"without={mb.get('stopped_by') or '-'}")
    if unpaired:
        lines.append(f"  unpaired: {', '.join(unpaired)}")
    # The floor: a score below FLOOR on any dimension, named, whatever the mean says.
    floors = []
    for r in active:
        scores = (r.get("review") or {}).get("scores") or {}
        low = [f"{k}={v}" for k, v in scores.items() if isinstance(v, int) and v < FLOOR]
        if low:
            floors.append(f"{r['engagement']} ({r['arm']}): {', '.join(low)}")
    lines.append("")
    lines.append(f"  floors (any score under {FLOOR}, not compensated by the mean): "
                 + ("; ".join(floors) if floors else "none"))
    # Breakdowns: never collapse across engineers or across the series' halves.
    by_engineer: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"with": [],
                                                                            "without": []})
    for r in active:
        if _quality(r) is not None:
            by_engineer[r.get("engineer", "?")][r["arm"]].append(_quality(r))
    if by_engineer:
        lines.append("  by engineer (mean quality):")
        for engineer, arms in sorted(by_engineer.items()):
            lines.append(f"    {engineer}: with {_mean(arms['with'])} (n={len(arms['with'])}), "
                         f"without {_mean(arms['without'])} (n={len(arms['without'])})")
    orders = sorted(r.get("order", 0) for r in active)
    if len(orders) >= 4:
        cut = orders[len(orders) // 2 - 1]
        halves = {"first half": [r for r in active if r.get("order", 0) <= cut],
                  "second half": [r for r in active if r.get("order", 0) > cut]}
        lines.append("  by order (mean quality, against learning):")
        for name, group in halves.items():
            w = [_quality(r) for r in group if r["arm"] == "with" and _quality(r) is not None]
            wo = [_quality(r) for r in group if r["arm"] == "without"
                  and _quality(r) is not None]
            lines.append(f"    {name}: with {_mean(w)} (n={len(w)}), without {_mean(wo)} "
                         f"(n={len(wo)})")
    # Blinding, per packet version, so a changed form does not erase the history.
    reviews = [r for r in active if r.get("review")]
    lines.append("")
    if reviews:
        by_version: dict[int, list[dict]] = defaultdict(list)
        for r in reviews:
            by_version[int(r["review"].get("packet_version", 1))].append(r)
        for version, group in sorted(by_version.items()):
            guesses = [r["review"]["arm_guess"] for r in group]
            decided = sum(1 for g in guesses if g != "uncertain")
            right = sum(1 for r in group if r["review"]["arm_guess"] == r["arm"])
            lines.append(f"  blinding, packet form v{version}: {right} of {decided} decided "
                         f"guesses were right ({len(guesses) - decided} uncertain, "
                         f"{len(group)} reviewed)")
    else:
        lines.append("  blinding: no reviews yet")
    lines.append(f"  pairs: {pairs}; reviews: {len(reviews)} of {n}")
    missing = [(r["engagement"], r["close"]["missing"]) for r in active
               if r.get("close") and r["close"]["missing"]]
    if missing:
        lines.append("  missing:")
        lines += [f"    {name}: {', '.join(keys)}" for name, keys in missing]
    unclosed = [r["engagement"] for r in active if not r.get("close")]
    if unclosed:
        lines.append(f"  not closed: {', '.join(unclosed)}")
    late = [r["engagement"] for r in active if r.get("built_already")]
    if late:
        lines.append(f"  started after a build existed: {', '.join(late)}")
    return "\n".join(lines)
