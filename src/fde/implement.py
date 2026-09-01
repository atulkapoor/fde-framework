"""Drive a coding agent until the emitted evals pass, inside guardrails.

The emitted project was always shaped for this loop: a harness that fails
until the pipeline is implemented, golden and adversarial sets, a boundary
that refuses at import, controls that fail closed. What was missing was the
driver -- something that hands the project to a coding agent with the harness
as the stop condition and the framework's own doctrine as the fence:

- **The loop is bounded.** A step cap, the same rule the posture section
  documents for the emitted system itself.
- **The exam is not editable.** The evals, the boundary, the controls and the
  decision documents are hashed before the first round; an agent that edits
  them is caught, the files are restored, and the loop stops loudly. A load
  test that passes because the agent rewrote it measures the rewrite.
- **Every round is on the record.** What the check said, what changed, and
  which check ended the loop.

The agent itself is a command -- `claude -p` by default, anything with the
same shape via --agent-cmd -- because which model implements is a decision
for the person running this, not for this module.
"""

from __future__ import annotations

import hashlib
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Files the agent must never change: the exam, the fence, and the record of
# what was decided. Globs, resolved at start.
PROTECTED = (
    "evals/*",
    "app/boundary.py",
    "app/controls.py",
    "ARCHITECTURE.md",
    "RISKS.md",
    "COMPLIANCE.md",
)

DEFAULT_AGENT = "claude -p --permission-mode acceptEdits"


@dataclass
class Round:
    number: int
    check_passed: bool
    check_tail: str
    changed: list[str] = field(default_factory=list)
    violation: str | None = None


@dataclass
class ImplementReport:
    rounds: list[Round]
    done: bool
    stopped_by: str  # "harness green" | "round cap" | "guardrail" | "agent failed"

    def log(self) -> str:
        lines = ["# Implementation log", ""]
        for r in self.rounds:
            lines.append(f"## Round {r.number}")
            lines.append("")
            lines.append(f"- check: {'green' if r.check_passed else 'red'}")
            if r.changed:
                lines.append(f"- changed: {', '.join(sorted(r.changed))}")
            if r.violation:
                lines.append(f"- **guardrail**: {r.violation}")
            if r.check_tail:
                lines.append("")
                lines.append("```")
                lines.append(r.check_tail)
                lines.append("```")
            lines.append("")
        lines.append(f"**Stopped by**: {self.stopped_by}.")
        lines.append("")
        return "\n".join(lines)


def _protected_files(project: Path) -> list[Path]:
    out: list[Path] = []
    for pattern in PROTECTED:
        out.extend(p for p in project.glob(pattern) if p.is_file())
    return out


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(project: Path) -> dict[Path, tuple[str, bytes]]:
    return {p: (_digest(p), p.read_bytes()) for p in _protected_files(project)}


def _tracked_files(project: Path) -> dict[Path, str]:
    return {
        p: _digest(p)
        for p in project.rglob("*.py")
        if ".implement" not in p.parts and "__pycache__" not in p.parts
    }


def _run_check(project: Path, check: str | None,
               extra: list[str] | None = None) -> tuple[bool, str]:
    # The same command the emitted CI runs -- the loop's green is CI's green.
    command = shlex.split(check) if check else [
        sys.executable, "evals/harness.py", "--min-score", "0.0",
    ]
    command = command + (extra or [])
    result = subprocess.run(  # noqa: S603 - the check is the caller's own command
        command, cwd=project, capture_output=True, text=True, timeout=1800,
    )
    tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-15:])
    return result.returncode == 0, tail


def _prompt(project: Path, check_tail: str) -> str:
    return (
        "You are implementing the emitted FDE project in this directory.\n\n"
        "Read ARCHITECTURE.md first: it says what was decided and why. "
        "Implement the scaffolded modules under app/components/ so the eval "
        "harness passes.\n\n"
        "Rules, not suggestions:\n"
        "- Never modify anything under evals/, app/boundary.py, "
        "app/controls.py, ARCHITECTURE.md, RISKS.md or COMPLIANCE.md. They "
        "are the exam and the fence; edits there are detected and reverted.\n"
        "- Do not weaken a gate, skip a critic, or catch an exception the "
        "controls raise on purpose.\n"
        "- Forbidden input (missing fields, type violations, empty "
        "documents) must raise app.contract.RefusedInput -- the adversarial "
        "layer treats that refusal as the correct answer, and a confident "
        "output on a forbidden probe as the failure.\n"
        "- Prefer the simplest implementation that passes; the corpus "
        "already rejected the clever alternatives for reasons RISKS.md and "
        "ARCHITECTURE.md record.\n\n"
        f"The check currently fails with:\n\n{check_tail}\n"
    )


def _run_agent(project: Path, agent_cmd: str, prompt: str) -> bool:
    """Run the agent with the brief on stdin, or via {prompt_file}.

    The placeholder exists because not every agent reads stdin: aider takes
    --message-file, and anything with the same shape slots in as
    --agent-cmd "aider --yes --message-file {prompt_file}".
    """
    stdin = prompt
    if "{prompt_file}" in agent_cmd:
        brief = project / ".implement" / "brief.md"
        brief.parent.mkdir(exist_ok=True)
        brief.write_text(prompt)
        # Absolute, because the agent runs with cwd=project: a relative
        # project path substituted here once produced delivery/delivery/...
        # from inside the project, and the agent died reading its own brief.
        agent_cmd = agent_cmd.replace("{prompt_file}", str(brief.resolve()))
        stdin = ""
    result = subprocess.run(  # noqa: S603 - the agent is the caller's own command
        shlex.split(agent_cmd),
        cwd=project, input=stdin, capture_output=True, text=True, timeout=3600,
    )
    return result.returncode == 0


def run_loop(
    project: Path,
    agent_cmd: str = DEFAULT_AGENT,
    max_rounds: int = 5,
    check: str | None = None,
    invoke_agent=None,
    holdout: Path | None = None,
) -> ImplementReport:
    """The loop. `invoke_agent` is injectable for tests."""
    project = Path(project)
    guarded = _snapshot(project)
    protected_dirs = [project / "evals"]
    known_protected = {
        path for directory in protected_dirs if directory.is_dir()
        for path in directory.rglob("*") if path.is_file()
    }
    invoke = invoke_agent or (lambda prompt: _run_agent(project, agent_cmd, prompt))
    rounds: list[Round] = []

    def green_report(number: int, tail: str) -> ImplementReport:
        if holdout is not None:
            held, held_tail = _run_check(
                project, check, extra=["--cases", str(Path(holdout).resolve())]
            )
            if not held:
                rounds.append(Round(number, False, held_tail,
                                    violation="green golden, red holdout -- "
                                              "the golden file may have been "
                                              "memorized; not accepting this"))
                return ImplementReport(rounds, done=False,
                                       stopped_by="holdout red")
            tail += "\nholdout: green (cases the implementer never saw)"
        rounds.append(Round(number, True, tail))
        return ImplementReport(rounds, done=True, stopped_by="harness green")

    for number in range(1, max_rounds + 1):
        passed, tail = _run_check(project, check)
        if passed:
            return green_report(number, tail)

        before = _tracked_files(project)
        agent_ok = invoke(_prompt(project, tail))

        # The exam stays the exam: restore anything protected that moved,
        # and remove anything NEW planted beside it -- a conftest.py dropped
        # into evals/ is not an edit the hash sees, but it is an edit.
        violations = []
        for path, (digest, body) in guarded.items():
            if not path.exists() or _digest(path) != digest:
                path.write_bytes(body)
                violations.append(str(path.relative_to(project)))
        for directory in protected_dirs:
            if not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if path.is_file() and path not in known_protected:
                    path.unlink()
                    violations.append(
                        f"{path.relative_to(project)} (planted, removed)"
                    )
        changed = [
            str(p.relative_to(project))
            for p, d in _tracked_files(project).items()
            if before.get(p) != d
        ] + [
            str(p.relative_to(project)) for p in before if not p.exists()
        ]

        if violations:
            rounds.append(Round(
                number, False, tail, changed,
                violation=f"the agent edited the exam ({', '.join(violations)}); "
                          f"restored, and stopping here",
            ))
            return ImplementReport(rounds, done=False, stopped_by="guardrail")

        rounds.append(Round(number, False, tail, changed))
        if not agent_ok and not changed:
            return ImplementReport(rounds, done=False, stopped_by="agent failed")

    passed, tail = _run_check(project, check)
    if passed:
        return green_report(max_rounds + 1, tail)
    rounds.append(Round(max_rounds + 1, passed, tail))
    return ImplementReport(rounds, done=False, stopped_by="round cap")
