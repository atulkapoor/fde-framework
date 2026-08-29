"""The engagement store.

An FDE is interrupted, offline, working across days, and talking to different
people. Four consequences shape this:

- **Append-only.** One file per session, never rewritten. Interrupted after four
  questions is a valid engagement, not a corrupt one.
- **One file per session.** Multi-respondent and multi-day fall out for free, and
  each file records who was talking and when.
- **The record is derived.** Recomputed from the sessions, never maintained. There
  is nothing to merge-conflict over, and it can be rebuilt at any moment.
- **Plain files.** No server, no database, no model. Works on a plane and inside
  an air gap, and a text editor is always a legal way in.

Layout::

    engagements/<name>/
      statements/     001.md, 002.md ...   prose, versioned, append-only
      facts/          0001-sponsor.yaml    one per session
      artifacts/      dropped files
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from fde.models.base import says_something
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.models.respondent import Respondent


@dataclass
class Session:
    """One sitting with one respondent. Written once, never edited."""

    session_id: str
    respondent: Respondent
    facts: list[Fact] = field(default_factory=list)

    def stamped(self) -> list[Fact]:
        """Facts carrying this session's respondent and id.

        The session already records who is talking, so a fact need not repeat it.
        Stamping here is what stops the two drifting apart.
        """
        return [
            f.model_copy(update={"respondent": self.respondent, "session_id": self.session_id})
            for f in self.facts
        ]

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            {
                "session_id": self.session_id,
                "respondent": {
                    "role": str(self.respondent.role),
                    "name": self.respondent.name,
                },
                "facts": [
                    # span and source are what make "where did that come from"
                    # answerable months later. Dropping them on write would
                    # quietly break the property the whole log exists for.
                    {
                        k: v
                        for k, v in (
                            ("dimension", f.dimension),
                            ("value", f.value),
                            ("provenance", str(f.provenance)),
                            ("kind", str(f.kind)),
                            ("span", list(f.span) if f.span else None),
                            ("source", f.source),
                        )
                        if v is not None
                    }
                    for f in self.facts
                ],
            },
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, text: str, source: str) -> Session:
        try:
            raw: dict[str, Any] = yaml.safe_load(text) or {}
            return cls(
                session_id=raw.get("session_id", source),
                respondent=Respondent(**raw["respondent"]),
                facts=[Fact(**_span_as_tuple(f)) for f in raw.get("facts", [])],
            )
        except Exception as exc:  # noqa: BLE001 - the file name is the useful part
            raise ValueError(f"{source}: cannot read session file -- {exc}") from exc


def _span_as_tuple(raw: dict[str, Any]) -> dict[str, Any]:
    """YAML gives back a list; Fact wants the tuple it was written from."""
    if isinstance(raw.get("span"), list):
        raw = {**raw, "span": tuple(raw["span"])}
    return raw


@dataclass
class Statement:
    """A version of the problem as stated. Version 1 is never edited."""

    version: int
    text: str
    reason: str | None = None


@dataclass
class Engagement:
    root: Path
    statements: list[Statement] = field(default_factory=list)
    profile: Profile = field(default_factory=Profile)

    # -- locations --------------------------------------------------------

    @property
    def facts_dir(self) -> Path:
        return self.root / "facts"

    @property
    def statements_dir(self) -> Path:
        return self.root / "statements"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    @property
    def baseline_path(self) -> Path:
        return self.root / "baseline.yaml"

    @property
    def gates_path(self) -> Path:
        return self.root / "gates.yaml"

    # -- writing ----------------------------------------------------------

    def append(self, session: Session) -> None:
        """Add a session. Never touches anything already written."""
        path = self.facts_dir / f"{session.session_id}.yaml"
        if path.exists():
            raise FileExistsError(f"{path}: session {session.session_id!r} already recorded")
        path.write_text(session.to_yaml())
        self.profile.ingest(session.stamped())

    def revise_statement(self, text: str, reason: str) -> None:
        version = len(self.statements) + 1
        self.statements.append(Statement(version=version, text=text, reason=reason))
        self._write_statement(self.statements[-1])

    def record_baseline(self, fields: dict[str, Any]) -> None:
        """Store the measured baseline. Validity is the gate's judgement, not
        a write condition: a partial baseline on disk is honest state, and
        status will say exactly what it still lacks."""
        self.baseline_path.write_text(yaml.safe_dump(fields, sort_keys=False))

    def baseline(self) -> dict[str, Any] | None:
        if not self.baseline_path.exists():
            return None
        return yaml.safe_load(self.baseline_path.read_text()) or None

    def record_data_access(self, note: str, at: str) -> None:
        state = self._raw_gate_state()
        state["data_access"] = {"note": note, "at": at}
        self._write_gate_state(state)

    def record_security_review(self, note: str, at: str) -> None:
        state = self._raw_gate_state()
        state["security_review"] = {"note": note, "at": at}
        self._write_gate_state(state)

    def record_waiver(self, gate: str, reason: str, at: str, against: str = "") -> None:
        """One waiver per gate, bound to the state it was granted against.

        Replaces rather than appends: waiving twice is one decision restated,
        and two identical lines in a risk section is noise. `against` is the
        gate's reason at the moment of waiving -- when that changes, the
        waiver no longer covers it, because nobody agreed to the new problem.
        """
        state = self._raw_gate_state()
        waivers = [
            w for w in state.get("overrides", [])
            if not (isinstance(w, dict) and w.get("gate") == gate)
        ]
        waivers.append({"gate": gate, "reason": reason, "at": at, "against": against})
        state["overrides"] = waivers
        self._write_gate_state(state)

    def _raw_gate_state(self) -> dict[str, Any]:
        """The file as written, for read-modify-write.

        Writers must not round-trip through the normalising reader: it is a
        filter, and filtering on write silently deleted hand-written content
        -- a mis-named attestation block vanished the moment somebody waived
        an unrelated gate. Unknown keys and odd shapes pass through a write
        untouched; only the reader ignores them.
        """
        if not self.gates_path.exists():
            return {}
        try:
            raw = yaml.safe_load(self.gates_path.read_text())
        except yaml.YAMLError as exc:
            raise ValueError(f"{self.gates_path}: cannot read gate state -- {exc}") from exc
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError(
                f"{self.gates_path}: expected a mapping of gate state, "
                f"found {type(raw).__name__}"
            )
        return raw

    def gate_state(self) -> dict[str, Any]:
        """Recorded gate state, normalised for the gate logic.

        Hand-editing this file is expected -- it is plain YAML in an
        engagement directory. Two things must not happen: a hand-edited
        shape reaching the gate logic as a traceback, and an unrecognised
        shape being read as permission. So every field the logic will touch
        comes out of here with its type guaranteed, and everything else is
        ignored on read (never deleted -- writers use the raw file).
        """
        raw = self._raw_gate_state()

        state: dict[str, Any] = {}
        access = raw.get("data_access")
        # Only a well-formed attestation counts: a mapping whose note a
        # person could read. A bare truthy value, a note of 0.0, or a
        # zero-width space must never read as evidence that credentials
        # returned rows -- that is the exact bypass this reader closes.
        if isinstance(access, dict) and says_something(access.get("note")):
            state["data_access"] = access

        review = raw.get("security_review")
        if isinstance(review, dict) and says_something(review.get("note")):
            state["security_review"] = review

        waivers = raw.get("overrides", [])
        if not isinstance(waivers, list):
            raise ValueError(
                f"{self.gates_path}: 'overrides' must be a list of waivers, "
                f"found {type(waivers).__name__}. A hand-edit that quietly "
                f"does nothing is worse than one that is refused."
            )
        kept = []
        for waiver in waivers:
            if not isinstance(waiver, dict):
                continue
            if not isinstance(waiver.get("gate"), str):
                continue
            if not says_something(waiver.get("reason")):
                continue
            against = waiver.get("against")
            kept.append({
                "gate": waiver["gate"],
                "reason": waiver["reason"],
                "at": str(waiver.get("at", "")),
                # Normalised to a string always. An explicit `against: null`
                # once meant "applies to whatever the gate says, forever" --
                # the unbounded waiver, reachable by typing one fewer word.
                # An empty string fails every match, so it fails closed.
                "against": against if isinstance(against, str) else "",
            })
        if kept:
            state["overrides"] = kept
        return state

    def _write_gate_state(self, state: dict[str, Any]) -> None:
        self.gates_path.write_text(yaml.safe_dump(state, sort_keys=False))

    def _write_statement(self, statement: Statement) -> None:
        path = self.statements_dir / f"{statement.version:03d}.md"
        header = f"<!-- version: {statement.version}"
        if statement.reason:
            header += f" | reason: {statement.reason}"
        path.write_text(f"{header} -->\n{statement.text}\n")

    # -- reading ----------------------------------------------------------

    def original_statement(self) -> Statement | None:
        """Version 1, always. The scope-drift gate measures against it."""
        return self.statements[0] if self.statements else None

    def current_statement(self) -> Statement | None:
        return self.statements[-1] if self.statements else None

    def rebuild(self) -> Profile:
        """Recompute the profile from what is on disk."""
        profile = Profile()
        for path in sorted(self.facts_dir.glob("*.yaml")):
            profile.ingest(Session.from_yaml(path.read_text(), path.stem).stamped())
        self.profile = profile
        return profile


def start_engagement(base: str | Path, name: str, statement: str | None = None) -> Engagement:
    """Create a new engagement. Refuses to overwrite an existing one."""
    root = Path(base) / name
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"{root}: engagement already exists")

    engagement = Engagement(root=root)
    for directory in (engagement.facts_dir, engagement.statements_dir, engagement.artifacts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    if statement:
        engagement.statements.append(Statement(version=1, text=statement))
        engagement._write_statement(engagement.statements[0])

    return engagement


def load_engagement(root: str | Path) -> Engagement:
    """Read an engagement back. Partial is valid; that is the point.

    Missing is not partial. A typo'd path that loads as a valid empty
    engagement lets every downstream command run against nothing --
    `architect` once happily printed a full design for a directory that did
    not exist.
    """
    root = Path(root)
    if not (root / "facts").is_dir():
        raise FileNotFoundError(
            f"{root}: no engagement here (no facts/ directory). "
            f"`fde start` creates one."
        )
    engagement = Engagement(root=root)

    for path in sorted(engagement.statements_dir.glob("*.md")):
        version, reason, text = _parse_statement(path.read_text(), path.stem)
        if version is None:
            # A stray file in statements/ is somebody's note, not a version.
            continue
        engagement.statements.append(Statement(version=version, text=text, reason=reason))

    engagement.rebuild()
    return engagement


def _parse_statement(text: str, stem: str) -> tuple[int | None, str | None, str]:
    try:
        version: int | None = int(stem)
    except ValueError:
        version = None
    reason = None
    lines = text.splitlines()
    if lines and lines[0].startswith("<!--"):
        header, lines = lines[0], lines[1:]
        for part in header.strip("<!->").split("|"):
            key, _, value = part.partition(":")
            if key.strip() == "version":
                try:
                    version = int(value.strip())
                except ValueError:
                    pass
            elif key.strip() == "reason":
                reason = value.strip()
    return version, reason, "\n".join(lines).strip()
