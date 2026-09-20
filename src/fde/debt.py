"""Decision debt: everything the engagement rests on that nobody has
settled, each item with an owner and an age.

A risk register lists what could go wrong. This lists what has not been
decided, verified or signed -- a gate still failing, a waiver standing in
for a condition, a fact the framework guessed or a person merely said
where a measurement was possible, two people disagreeing, an attestation
with no name on it, a role never asked, an incident open, a component
nothing serves -- read off the record, never declared. An item blocks the
build, blocks production, or is informational, and ages from the date it
went on the record where the record has one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from fde.lifecycle import open_incidents
from fde.models.base import DimensionKind, Provenance
from fde.stakeholders import build as stakeholder_map

AGING_DAYS = 30

GATE_OWNERS = {
    "data_access": "admin", "baseline_capture": "sponsor", "outcome_contract": "sponsor",
    "client_readiness": "eval_owner", "security_review": "admin", "scope_drift": "sponsor",
    "offline_evaluability": "eval_owner", "licence_compatibility": "sponsor",
}


@dataclass
class Item:
    kind: str
    what: str
    owner: str
    blocks: str  # build | production | ""
    since: str | None = None
    remedy: str = ""

    def age(self, as_of: date) -> int | None:
        if not self.since:
            return None
        try:
            return (as_of - date.fromisoformat(str(self.since)[:10])).days
        except ValueError:
            return None


def collect(engagement, status, architecture, registry, as_of: str | None = None) -> list[Item]:
    root = Path(engagement.root)
    items: list[Item] = []
    waived = {o.gate for o in status.overridden}
    for gate in status.gates:
        if not gate.passed and gate.name not in waived:
            items.append(Item("gate", f"{gate.name}: {gate.reason}", GATE_OWNERS.get(gate.name,
                              "sponsor"), "build", None, gate.remedy))
    raw = engagement._raw_gate_state() if hasattr(engagement, "_raw_gate_state") else {}
    for waiver in (raw.get("overrides") or []) if isinstance(raw, dict) else []:
        if isinstance(waiver, dict) and waiver.get("gate"):
            items.append(Item("waiver", f"{waiver['gate']}: {waiver.get('reason', '')}",
                              waiver.get("by") or GATE_OWNERS.get(waiver["gate"], "sponsor"),
                              "production", waiver.get("at"),
                              "meet the gate, or restate the waiver if it still holds"))
    profile = engagement.profile
    referenced = set()
    for decision in architecture.decisions.values():
        approach = registry.approaches.get(decision.approach) if decision.approach else None
        for predicate in (getattr(approach, "applies_when", None),
                          getattr(approach, "avoid_when", None)):
            referenced.update(_dimensions_in(predicate))
    for dimension in profile.dimensions():
        fact = profile.fact(dimension)
        if fact is None:
            continue
        entry = registry.dimensions.get(dimension)
        owner = (entry.ask_role[0] if entry is not None and entry.ask_role else "sponsor")
        cited = dimension in referenced
        if fact.provenance == Provenance.INFERRED:
            items.append(Item("guessed", f"{dimension} = {fact.value}: the framework's own "
                              "inference", owner, "production" if cited else "", None,
                              f"confirm it: fde ask <eng> --role {owner}"))
        elif fact.provenance == Provenance.INTERVIEW and fact.kind == DimensionKind.ENVIRONMENT:
            items.append(Item("stated", f"{dimension} = {fact.value}: said by "
                              f"{fact.respondent}, measurable but not measured", owner,
                              "production" if cited else "", None,
                              "measure it: fde scan, or a document the client owns"))
    for disagreement in profile.disagreements():
        who = "; ".join(f"{f.respondent} said {f.value}" for f in disagreement.facts)
        items.append(Item("disagreement", f"{disagreement.dimension}: {who}", "sponsor", "",
                          None, "settle it in the room and record who was right"))
    people = stakeholder_map(engagement)
    for what in people.unsigned:
        items.append(Item("unsigned", what, "unsigned", "", _date_in(what),
                          "re-record with --by, or leave it and know it"))
    for role in people.unheard:
        items.append(Item("unheard", f"{role} has never been asked", role, "", None,
                          f"fde ask <eng> --role {role}"))
    for incident in open_incidents(root):
        items.append(Item("incident", f"{incident.get('id')}: {incident.get('kind')}",
                          "eval_owner", "production", incident.get("opened_at"),
                          str(incident.get("next", ""))[:120]))
    for component in architecture.decisions.undecided():
        items.append(Item("undecided", f"{component}: no approach in the registry serves it",
                          "sponsor", "production", None,
                          "answer what it waits on (fde next), or extend the registry"))
    for component, decision in architecture.decisions.items():
        if decision.approach and str(decision.confidence) == "low":
            items.append(Item("low-confidence", f"{component}: {decision.approach} -- "
                              f"{decision.rationale[:100]}", "eval_owner", "", None,
                              "verify at source before production"))
    return items


def _dimensions_in(predicate) -> set[str]:
    if predicate is None:
        return set()
    try:
        from fde.predicate import referenced
        return set(referenced(predicate))
    except Exception:  # noqa: BLE001 -- an unparseable predicate cites nothing
        return set()


def _date_in(text: str) -> str | None:
    import re
    match = re.search(r"\((\d{4}-\d{2}-\d{2})\)", text)
    return match.group(1) if match else None


def render(items: list[Item], name: str, as_of: str | None = None) -> str:
    today = date.fromisoformat(as_of) if as_of else date.today()
    lines = [f"{name}: decision debt as of {today.isoformat()}", ""]
    if not items:
        lines.append("  nothing outstanding on the record")
        return "\n".join(lines)
    groups = [("blocking the build", [i for i in items if i.blocks == "build"]),
              ("blocking production", [i for i in items if i.blocks == "production"]),
              ("open", [i for i in items if not i.blocks])]
    aging = 0
    for title, group in groups:
        if not group:
            continue
        lines.append(f"  {title} ({len(group)})")
        for item in group:
            age = item.age(today)
            stamp = f"  {age} day(s)" if age is not None else ""
            if age is not None and age >= AGING_DAYS:
                aging += 1
                stamp += " AGING"
            lines.append(f"    {item.kind:14} {item.what}")
            lines.append(f"    {'':14} owner: {item.owner}{stamp}")
            if item.remedy:
                lines.append(f"    {'':14} next: {item.remedy}")
        lines.append("")
    blocking = sum(1 for i in items if i.blocks == "build")
    production = sum(1 for i in items if i.blocks == "production")
    unsigned = sum(1 for i in items if i.kind == "unsigned")
    lines.append(f"{len(items)} item(s): {blocking} blocking the build, {production} blocking "
                 f"production, {aging} older than {AGING_DAYS} days, {unsigned} unsigned")
    return "\n".join(lines)
