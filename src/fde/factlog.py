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
                    {
                        "dimension": f.dimension,
                        "value": f.value,
                        "provenance": str(f.provenance),
                        "kind": str(f.kind),
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
                facts=[Fact(**f) for f in raw.get("facts", [])],
            )
        except Exception as exc:  # noqa: BLE001 - the file name is the useful part
            raise ValueError(f"{source}: cannot read session file -- {exc}") from exc


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
    """Read an engagement back. Partial is valid; that is the point."""
    root = Path(root)
    engagement = Engagement(root=root)

    for path in sorted(engagement.statements_dir.glob("*.md")):
        version, reason, text = _parse_statement(path.read_text(), path.stem)
        engagement.statements.append(Statement(version=version, text=text, reason=reason))

    engagement.rebuild()
    return engagement


def _parse_statement(text: str, stem: str) -> tuple[int, str | None, str]:
    version, reason = int(stem), None
    lines = text.splitlines()
    if lines and lines[0].startswith("<!--"):
        header, lines = lines[0], lines[1:]
        for part in header.strip("<!->").split("|"):
            key, _, value = part.partition(":")
            if key.strip() == "version":
                version = int(value.strip())
            elif key.strip() == "reason":
                reason = value.strip()
    return version, reason, "\n".join(lines).strip()
