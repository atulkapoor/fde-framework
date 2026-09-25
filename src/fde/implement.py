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
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Files the agent must never change: the exam, the fence, and the record of
# what was decided. Globs, resolved at start.
PROTECTED = (
    "evals/*",
    "tests/*",
    "app/boundary.py",
    "app/controls.py",
    "app/contract.py",
    "pyproject.toml",
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
    provisional: bool = False
    sandbox: str = ""  # where the agent ran, in words, for the log

    def log(self) -> str:
        lines = ["# Implementation log", ""]
        if self.sandbox:
            lines += [f"- the agent ran on: {self.sandbox}", ""]
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
        if self.provisional:
            lines.append("")
            lines.append("**Provisional**: this build is judged and the judge is not yet "
                         "calibrated; no score above is quotable until `evals/calibrate.py` "
                         "passes on hand-graded cases.")
        lines.append("")
        return "\n".join(lines)


def _protected_files(project: Path) -> list[Path]:
    out: list[Path] = []
    for pattern in PROTECTED:
        out.extend(p for p in project.glob(pattern) if p.is_file())
    return out


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _holdout_score(project: Path, holdout: Path | str, timeout: float) -> float | None:
    """The harness's own holdout score for the project as it stands, read
    from a report the harness writes; None when it cannot be measured."""
    import tempfile

    harness = project / "evals" / "harness.py"
    if not harness.exists():
        return None
    with tempfile.TemporaryDirectory() as scratch:
        report = Path(scratch) / "holdout.json"
        try:
            subprocess.run(
                [sys.executable, "evals/harness.py", "--cases", str(Path(holdout).resolve()),
                 "--report", str(report), "--allow-uncalibrated"],
                cwd=project, capture_output=True, text=True, timeout=timeout,
            )
            layer = json.loads(report.read_text())["layers"][0]
        except (subprocess.TimeoutExpired, OSError, ValueError, KeyError, IndexError):
            return None
    score = layer.get("score")
    return float(score) if isinstance(score, (int, float)) else None


def _without_bar(check: str | None) -> str | None:
    """The check command with its golden bar removed, for the holdout run.
    The default check (None) carries its bar inside _run_check, where the
    holdout pass never adds one."""
    if not check:
        return check
    return re.sub(r"\s--min-score(?:=|\s+)\S+", "", check)


def _holdout_provenance(project: Path, holdout: Path) -> str:
    """One line when the holdout is not the file the build recorded.

    A green against a holdout nobody can tie to the split is a green
    against an unknown exam -- 36 verified pairs once went missing between
    the split and the file handed to this check, and nothing said so."""
    manifest = project / "evals" / "manifest.json"
    if not manifest.exists():
        return ""
    try:
        recorded = (json.loads(manifest.read_text()).get("holdout") or {}).get("sha256")
    except (ValueError, AttributeError):
        return ""
    if not recorded:
        return ""
    actual = hashlib.sha256(holdout.read_bytes()).hexdigest()
    if actual == recorded:
        return " -- the file the build recorded"
    return (f"\nholdout: NOT the file recorded at build (sha256 {actual[:12]} != "
            f"{recorded[:12]}) -- the exam changed since the build; this green is "
            f"against a different exam than the one on record")


def _snapshot(project: Path) -> dict[Path, tuple[str, bytes]]:
    return {p: (_digest(p), p.read_bytes()) for p in _protected_files(project)}


def _tracked_files(project: Path) -> dict[Path, str]:
    return {
        p: _digest(p)
        for p in project.rglob("*.py")
        if ".implement" not in p.parts and "__pycache__" not in p.parts
    }


def _own_tests_red(project: Path, timeout: float) -> str | None:
    """The deliverable's own tests are the floor beneath the harness: a
    round that breaks the contract, the fence or lint is red before the
    exam is asked. Returns the failing tail, or None when green or absent."""
    tests = project / "tests"
    if not tests.is_dir() or not any(tests.glob("test_*.py")):
        return None
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/"],
        cwd=project, capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode == 0:
        return None
    return "own tests red:\n" + (result.stdout + result.stderr)[-1500:]


def _run_check(project: Path, check: str | None,
               extra: list[str] | None = None,
               timeout: float = 1800.0) -> tuple[bool, str]:
    # CI's floor is 0.0 -- "no regression". The loop's job is different:
    # finish. A default bar of zero once declared a 70% implementation done
    # and handed it to the holdout, whose verdict then read a half-built
    # system as a memorized exam. The loop drives to the acceptance-grade
    # bar unless the caller sets another with --check.
    command = shlex.split(check) if check else [
        sys.executable, "evals/harness.py", *([] if extra else ["--min-score", "0.85"]),
    ]
    if not extra:
        red = _own_tests_red(project, timeout)
        if red is not None:
            return False, red
    # The loop drives to green BEFORE a judge can be calibrated (calibration
    # needs answers to grade), so a judged build's green is provisional and
    # asked for by name; the report says so where the loop stops.
    if "--allow-uncalibrated" not in command and (project / "evals" / "calibrate.py").exists():
        command = command + ["--allow-uncalibrated"]
    command = command + (extra or [])
    try:
        result = subprocess.run(  # noqa: S603 - the check is the caller's own command
            command, cwd=project, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, (
            f"the check exceeded its {timeout:.0f}s budget -- a model in "
            f"the eval loop makes honest runs slow; raise --check-timeout, "
            f"shrink the exam, or speed up the model"
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


class AgentMissing(RuntimeError):
    """The coding agent's command is not on this machine."""


def _run_agent(project: Path, agent_cmd: str, prompt: str,
               timeout: float = 3600.0, sandbox: str | None = None,
               env_allow: tuple[str, ...] = (), allow_network: bool = False) -> bool:
    """Run the agent with the brief on stdin, or via {prompt_file}.

    The placeholder exists because not every agent reads stdin: aider takes
    --message-file, and anything with the same shape slots in as
    --agent-cmd "aider --yes --message-file {prompt_file}".

    With `sandbox="docker"` the agent runs in a container with only the
    project mounted, the environment reduced to the policy's allowlist and
    the network off unless allowed -- see fde.sandbox.
    """
    stdin = prompt
    if "{prompt_file}" in agent_cmd:
        brief = project / ".implement" / "brief.md"
        brief.parent.mkdir(exist_ok=True)
        brief.write_text(prompt)
        # Absolute, because the agent runs with cwd=project: a relative
        # project path substituted here once produced delivery/delivery/...
        # from inside the project, and the agent died reading its own brief.
        if sandbox == "docker":
            from fde.sandbox import WORKDIR
            agent_cmd = agent_cmd.replace("{prompt_file}", f"{WORKDIR}/.implement/brief.md")
        else:
            agent_cmd = agent_cmd.replace("{prompt_file}", str(brief.resolve()))
        stdin = ""
    try:
        if sandbox == "docker":
            from fde.sandbox import load_policy, run_agent_in_sandbox
            result = run_agent_in_sandbox(project, agent_cmd, stdin, timeout,
                                          load_policy(project), env_allow, allow_network)
        else:
            result = subprocess.run(  # noqa: S603 - the agent is the caller's own command
                shlex.split(agent_cmd),
                cwd=project, input=stdin, capture_output=True, text=True,
                timeout=timeout,
            )
    except subprocess.TimeoutExpired:
        # A model-in-the-loop round can legitimately outlive any fixed
        # budget -- the receipts demonstration's local-inference rounds ran
        # past an hour. A budget overrun is a round result, never a
        # traceback.
        error_file = project / ".implement" / "agent-last-error.txt"
        error_file.parent.mkdir(exist_ok=True)
        error_file.write_text(
            f"TIMEOUT: agent exceeded its {timeout:.0f}s budget -- raise "
            f"it with --agent-timeout, shrink the exam, or speed up the "
            f"model"
        )
        return False
    except FileNotFoundError as exc:
        if sandbox == "docker":
            raise AgentMissing(
                "docker is not on this machine; --sandbox docker needs it. Install it, "
                "or run without --sandbox and rely on the fence alone."
            ) from exc
        raise AgentMissing(
            f"the coding agent {shlex.split(agent_cmd)[0]!r} is not on this "
            f"machine. Install it, or name another with --agent-cmd -- "
            f'e.g. --agent-cmd "aider --yes --message-file {{prompt_file}}". '
            f"(An IDE-extension install of Claude Code bundles the binary "
            f"without putting it on PATH -- point --agent-cmd at it.)"
        ) from exc
    if result.returncode != 0:
        # Why the agent failed belongs in the log, not in the void: a
        # transient rate limit and a broken command read identically as
        # "agent failed" without it.
        error_file = project / ".implement" / "agent-last-error.txt"
        error_file.parent.mkdir(exist_ok=True)
        error_file.write_text((result.stdout + result.stderr)[-2000:])
    return result.returncode == 0


def run_loop(
    project: Path,
    agent_cmd: str = DEFAULT_AGENT,
    max_rounds: int = 5,
    check: str | None = None,
    invoke_agent=None,
    holdout: Path | None = None,
    agent_timeout: float = 3600.0,
    check_timeout: float = 1800.0,
    sandbox: str | None = None,
    env_allow: tuple[str, ...] = (),
    allow_network: bool = False,
) -> ImplementReport:
    """The loop. `invoke_agent` is injectable for tests."""
    project = Path(project)
    guarded = _snapshot(project)
    protected_dirs = [project / "evals"]
    known_protected = {
        path for directory in protected_dirs if directory.is_dir()
        for path in directory.rglob("*") if path.is_file()
    }
    invoke = invoke_agent or (
        lambda prompt: _run_agent(project, agent_cmd, prompt, agent_timeout, sandbox,
                                  env_allow, allow_network))
    rounds: list[Round] = []

    # The shipped baseline's own holdout score, measured before any round:
    # a round that clears the golden bar and lands BELOW it has traded
    # generalisation for the exam, whatever the harness's floor says.
    baseline_holdout = _holdout_score(project, holdout, check_timeout) if holdout else None

    def green_report(number: int, tail: str) -> ImplementReport:
        if holdout is not None:
            # The holdout is scored against the harness's own holdout gate
            # (the majority rate, the exclusive half-right floor), never
            # against the golden bar: the golden score is in-sample wherever
            # the baseline is fitted on it, and a bar set for it once refused
            # an implementation that had raised the holdout by three points.
            held, held_tail = _run_check(
                project, _without_bar(check), extra=["--cases", str(Path(holdout).resolve())],
                timeout=check_timeout,
            )
            if not held:
                rounds.append(Round(number, False, held_tail,
                                    violation="the check cleared its bar, and "
                                              "cases the implementer never saw "
                                              "failed -- a memorized golden "
                                              "file, or a bar too low to mean "
                                              "finished; not accepting this"))
                return ImplementReport(rounds, done=False,
                                       stopped_by="holdout red")
            achieved = _holdout_score(project, holdout, check_timeout)
            if (baseline_holdout is not None and achieved is not None
                    and achieved < baseline_holdout - 0.005):
                rounds.append(Round(number, False, held_tail,
                                    violation=f"the holdout fell from the shipped baseline's "
                                              f"{baseline_holdout:.1%} to {achieved:.1%}: "
                                              f"the round traded generalisation for the "
                                              f"exam; not accepting this"))
                return ImplementReport(rounds, done=False, stopped_by="holdout below baseline")
            tail += "\nholdout: green (cases the implementer never saw)"
            if achieved is not None:
                tail += f" -- {achieved:.1%}"
                if baseline_holdout is not None:
                    tail += f" (shipped baseline {baseline_holdout:.1%})"
            tail += _holdout_provenance(project, Path(holdout))
        rounds.append(Round(number, True, tail))
        provisional = ((project / "evals" / "calibrate.py").exists()
                       and not (project / "evals" / "judge-calibration.json").exists())
        return ImplementReport(rounds, done=True, stopped_by="harness green",
                               provisional=provisional)

    for number in range(1, max_rounds + 1):
        passed, tail = _run_check(project, check, timeout=check_timeout)
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
                # The interpreter is not the agent: importing evals/taxonomy
                # writes a __pycache__ beside it on the very first harness
                # run, and treating bytecode as a planted exam edit stopped
                # every real loop at round 1.
                if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                    continue
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
        if not agent_ok:
            error_file = project / ".implement" / "agent-last-error.txt"
            said = ""
            if error_file.exists():
                said = " ".join(error_file.read_text().split())[-300:]
            # A burned budget must be visible even when the agent left
            # edits behind -- five silent 3600s rounds is a day nobody
            # gets back. And a timeout is a timeout, never "exited".
            if said.startswith("TIMEOUT:"):
                rounds[-1].violation = f"the agent round timed out: {said[8:].strip()}"
            elif said:
                rounds[-1].violation = f"the agent command exited nonzero: {said}"
            if not changed:
                return ImplementReport(rounds, done=False, stopped_by="agent failed")

    passed, tail = _run_check(project, check, timeout=check_timeout)
    if passed:
        return green_report(max_rounds + 1, tail)
    rounds.append(Round(max_rounds + 1, passed, tail))
    return ImplementReport(rounds, done=False, stopped_by="round cap")
