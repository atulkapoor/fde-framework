"""The stakeholder map: who has been heard, who owns what, who signed for
what, and which roles the engagement has never spoken to.

The interview is scoped by role because different people know different
things, and every fact already carries the role -- and, when given, the
name -- of who said it. Attestations, waivers, deployments and outcomes
carry who signed them when the command was told (`--by`). This reads all
of that back as one map and names the gaps: a role nobody has asked, an
attestation nobody signed. It is a map of the engagement's people as the
record shows them, not a contact list; nothing here is a phone number.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from fde.models.respondent import Role

STAKES = {
    Role.SPONSOR.value: "success criteria, budget, political constraints",
    Role.EVAL_OWNER.value: "what separates excellent from acceptable",
    Role.USER.value: "the real workflow and its exceptions",
    Role.ADMIN.value: "data access, audit, topology, entitlements",
    Role.SKEPTIC.value: "why the last attempts failed",
}
CLIENT_ROLES = tuple(STAKES)


@dataclass
class Person:
    name: str
    role: str
    stake: str = ""
    at: str = ""
    note: str = ""


@dataclass
class RoleRow:
    role: str
    stake: str
    named: list[str] = field(default_factory=list)
    sessions: int = 0
    facts: int = 0
    heard_from: list[str] = field(default_factory=list)
    signed: list[str] = field(default_factory=list)

    @property
    def heard(self) -> bool:
        return self.sessions > 0


@dataclass
class StakeholderMap:
    rows: list[RoleRow]
    unsigned: list[str]
    others: list[Person]

    @property
    def unheard(self) -> list[str]:
        return [row.role for row in self.rows if not row.heard]


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


def add(engagement, name: str, role: str, stake: str = "", at: str | None = None,
        note: str = "") -> dict:
    """Name a person on the record. Appends; a person named twice is two
    lines, the later one read as current."""
    entry = {"name": name.strip(), "role": role.strip(), "stake": stake.strip(),
             "at": at or date.today().isoformat(), "note": note.strip()}
    with (Path(engagement.root) / "stakeholders.jsonl").open("a") as handle:
        handle.write(json.dumps(entry) + "\n")
    return entry


def people(engagement) -> list[Person]:
    seen: dict[str, Person] = {}
    for row in _jsonl(Path(engagement.root) / "stakeholders.jsonl"):
        if row.get("name"):
            seen[row["name"]] = Person(row["name"], row.get("role", ""), row.get("stake", ""),
                                       row.get("at", ""), row.get("note", ""))
    return list(seen.values())


def _sessions(engagement) -> dict[str, dict]:
    """Per role: sessions held, facts recorded, names on them."""
    out: dict[str, dict] = {}
    facts_dir = Path(engagement.root) / "facts"
    if not facts_dir.is_dir():
        return out
    for path in sorted(facts_dir.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            continue
        respondent = raw.get("respondent") or {}
        role = str(respondent.get("role", ""))
        entry = out.setdefault(role, {"sessions": 0, "facts": 0, "names": []})
        entry["sessions"] += 1
        entry["facts"] += len(raw.get("facts") or [])
        name = respondent.get("name")
        if name and name not in entry["names"]:
            entry["names"].append(str(name))
    return out


def signatures(engagement) -> list[tuple[str | None, str]]:
    """(who, what) for everything on the record that somebody could have
    signed: attestations, waivers, incident closures, outcomes."""
    root = Path(engagement.root)
    sigs: list[tuple[str | None, str]] = []
    raw = engagement._raw_gate_state() if hasattr(engagement, "_raw_gate_state") else {}
    if isinstance(raw, dict):
        for key in ("data_access", "security_review", "deployed"):
            entry = raw.get(key)
            if isinstance(entry, dict) and entry.get("note"):
                sigs.append((entry.get("by") or None, f"{key} ({entry.get('at', '')})"))
        for waiver in raw.get("overrides") or []:
            if isinstance(waiver, dict) and waiver.get("gate"):
                sigs.append((waiver.get("by") or None,
                             f"waiver {waiver['gate']} ({waiver.get('at', '')})"))
    for incident in _jsonl(root / "incidents.jsonl"):
        if incident.get("status") == "closed":
            sigs.append((incident.get("closed_by") or None,
                         f"closed {incident.get('id')} ({incident.get('closed_at', '')})"))
    for outcome in _jsonl(root / "outcomes.jsonl"):
        sigs.append((outcome.get("by") or None,
                     f"outcome {outcome.get('metric')} ({outcome.get('at', '')})"))
    return sigs


def build(engagement) -> StakeholderMap:
    named = people(engagement)
    heard = _sessions(engagement)
    sigs = signatures(engagement)
    rows = []
    for role in CLIENT_ROLES:
        row = RoleRow(role, STAKES[role])
        row.named = [p.name for p in named if p.role == role]
        entry = heard.get(role, {})
        row.sessions = entry.get("sessions", 0)
        row.facts = entry.get("facts", 0)
        row.heard_from = list(entry.get("names", []))
        known = set(row.named) | set(row.heard_from)
        row.signed = [what for by, what in sigs if by and by in known]
        rows.append(row)
    unsigned = [what for by, what in sigs if not by]
    others = [p for p in named if p.role not in CLIENT_ROLES]
    return StakeholderMap(rows, unsigned, others)


def render(stakeholders: StakeholderMap, name: str) -> str:
    lines = [f"{name}: stakeholders", ""]
    for row in stakeholders.rows:
        who = ", ".join(row.named) if row.named else "--"
        if row.heard:
            heard = f"{row.sessions} session(s), {row.facts} fact(s)"
            if row.heard_from:
                heard += " from " + ", ".join(row.heard_from)
        else:
            heard = f"never heard: fde ask <eng> --role {row.role}"
        lines.append(f"  {row.role:11} {who:28} {heard}")
        lines.append(f"  {'':11} {'owns:':28} {row.stake}")
        if row.signed:
            lines.append(f"  {'':11} {'signed:':28} {'; '.join(row.signed)}")
    if stakeholders.others:
        lines += ["", "outside the five roles: " + ", ".join(
            f"{p.name} ({p.role})" for p in stakeholders.others)]
    if stakeholders.unheard:
        lines += ["", "unheard: " + ", ".join(stakeholders.unheard)]
    if stakeholders.unsigned:
        lines += ["", "on the record with nobody's name on it: " + "; ".join(stakeholders.unsigned)
                  + "  (pass --by next time)"]
    return "\n".join(lines)
