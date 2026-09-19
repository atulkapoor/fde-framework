"""Production grade, measured: one command that runs what a deliverable can
prove about itself and writes the numbers down.

"Not production grade" is a judgement; this is the measurement it should
rest on. Every line is something the project itself can be made to show --
its own tests, its own lint, its own exam layer by layer, the holdout the
engagement kept, the exam record, the judge's calibration, the boot
refusals, what the risk register still lists as unimplemented -- with the
number beside the verdict, so two people arguing about whether a build is
ready are arguing about a row, not an adjective.

    fde scorecard <project> [--holdout <jsonl>] [--min-score 0.0]

Writes SCORECARD.md and scorecard.json into the project. Exit status is the
verdict: 0 when every measured property holds, 1 otherwise. Properties the
build cannot measure (no holdout given, no judge, no training path) are
reported as not applicable, never as passes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROTOCOL_FLOOR = 30  # evals/acceptance.md's own sample floor


@dataclass
class Row:
    property: str
    measured: str
    holds: bool | None  # None: not applicable here
    why: str = ""


@dataclass
class Scorecard:
    project: str
    rows: list[Row] = field(default_factory=list)

    @property
    def measured(self) -> list[Row]:
        return [r for r in self.rows if r.holds is not None]

    @property
    def failing(self) -> list[Row]:
        return [r for r in self.rows if r.holds is False]

    @property
    def verdict(self) -> str:
        held = len(self.measured) - len(self.failing)
        return f"{held} of {len(self.measured)} measured properties hold"

    def add(self, property: str, measured: str, holds: bool | None, why: str = "") -> None:
        self.rows.append(Row(property, measured, holds, why))


def _run(argv: list[str], cwd: Path, timeout: float, env: dict | None = None):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          env={"PATH": os.environ.get("PATH", "/usr/bin"), **(env or {})})


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# --- the measurements --------------------------------------------------------


def own_tests(card: Scorecard, project: Path, timeout: float) -> None:
    if not (project / "tests").is_dir():
        card.add("own tests", "no tests/ directory", False, "the deliverable ships none")
        return
    result = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/"],
                  project, timeout)
    tail = (result.stdout.strip().splitlines() or ["no output"])[-1]
    card.add("own tests", tail, result.returncode == 0,
             "the deliverable's own smoke and edge tests, model-free")


def lint(card: Scorecard, project: Path, timeout: float) -> None:
    try:
        import ruff  # noqa: F401
    except ImportError:
        card.add("lint", "ruff not installed", None)
        return
    result = _run([sys.executable, "-m", "ruff", "check", "--isolated", "--select", "F,E,W,I,B,UP",
                   "--line-length", "100", "."], project, timeout)
    card.add("lint", "clean" if result.returncode == 0 else
             (result.stdout.strip().splitlines() or ["errors"])[-1], result.returncode == 0)


def exam(card: Scorecard, project: Path, timeout: float, min_score: float,
         env: dict | None) -> dict | None:
    harness = project / "evals" / "harness.py"
    if not harness.exists():
        card.add("exam", "no evals/harness.py", False)
        return None
    report = project / "scorecard-harness.json"
    result = _run([sys.executable, "evals/harness.py", "--min-score", str(min_score),
                   "--report", str(report), "--allow-uncalibrated"],
                  project, timeout, env)
    if not report.exists():
        card.add("exam", "the harness wrote no report", False, result.stderr[-300:])
        return None
    written = json.loads(report.read_text())
    layers = {layer["layer"]: layer for layer in written.get("layers", [])}
    in_sample = "in-sample" in result.stdout
    for name in ("golden", "edge_case", "adversarial"):
        layer = layers.get(name)
        if not layer or not layer.get("cases"):
            card.add(f"exam: {name}", "0 cases", False, "an empty layer measures nothing")
            continue
        score = layer.get("score")
        note = ""
        holds = True
        if layer.get("decision"):
            majority = layer["decision"]["majority_rate"]
            note = f"majority {majority:.1%}"
            holds = score > majority
        if name == "adversarial":
            holds = score >= 1.0 and not layer.get("errors")
            failures = layer.get("failures", [])
            followed = sum(1 for f in failures if f.get("followed"))
            misread = sum(1 for f in failures if f.get("misread"))
            note = f"{followed} followed, {misread} on misread bases"
        if name == "golden" and in_sample:
            note = (note + "; " if note else "") + "in-sample: the baseline is fitted on this file"
        if layer.get("form") is not None:
            note = (note + "; " if note else "") + f"form {layer['form']:.1%}"
        card.add(f"exam: {name}", f"{score:.1%} on {layer['cases']} cases"
                 + (f" ({note})" if note else ""), holds)
    card.add("exam: verdict", "green" if result.returncode == 0 else
             (result.stderr.strip().splitlines() or ["red"])[-1][:160], result.returncode == 0,
             "the harness's own exit status at --min-score " + str(min_score))
    if written.get("judged"):
        calibration = written.get("calibration") or {}
        card.add("judge calibration",
                 "passed" if calibration.get("calibrated") else "none on record",
                 bool(calibration.get("calibrated")),
                 "a judged score is not quotable until evals/calibrate.py passes")
    return written


def holdout(card: Scorecard, project: Path, path: Path | None, timeout: float,
            env: dict | None) -> None:
    manifest = project / "evals" / "manifest.json"
    recorded = None
    if manifest.exists():
        try:
            recorded = (json.loads(manifest.read_text()).get("holdout") or {}).get("sha256")
        except (ValueError, AttributeError):
            recorded = None
    if path is None:
        card.add("holdout", "not given", None,
                 "the out-of-sample number; pass --holdout <engagement>/artifacts/holdout.jsonl")
        return
    if not path.exists():
        card.add("holdout", f"{path} missing", False)
        return
    cases = sum(1 for line in path.read_text().splitlines() if line.strip())
    report = project / "scorecard-holdout.json"
    result = _run([sys.executable, "evals/harness.py", "--cases", str(path.resolve()),
                   "--report", str(report), "--allow-uncalibrated"], project, timeout, env)
    if not report.exists():
        card.add("holdout", "the harness wrote no report", False, result.stderr[-300:])
        return
    layer = json.loads(report.read_text())["layers"][0]
    score = layer.get("score") or 0.0
    note = ""
    holds = result.returncode == 0
    if layer.get("decision"):
        majority = layer["decision"]["majority_rate"]
        note = f"majority {majority:.1%}"
        holds = holds and score > majority
    card.add("holdout", f"{score:.1%} on {cases} cases" + (f" ({note})" if note else ""), holds,
             "cases the delivery never shipped; the harness's holdout floor applies")
    card.add("holdout: sample size", f"{cases} cases",
             cases >= PROTOCOL_FLOOR,
             f"the acceptance protocol's floor is {PROTOCOL_FLOOR}")
    if recorded:
        actual = _digest(path)
        card.add("holdout: the file on record", "matches evals/manifest.json"
                 if actual == recorded else f"differs ({actual[:12]} != {recorded[:12]})",
                 actual == recorded)


def exam_record(card: Scorecard, project: Path) -> None:
    manifest = project / "evals" / "manifest.json"
    if not manifest.exists():
        card.add("exam record", "no evals/manifest.json", False,
                 "the split seed, share and digests of every eval file")
        return
    try:
        record = json.loads(manifest.read_text())
    except ValueError:
        card.add("exam record", "unreadable", False)
        return
    mismatched = []
    for name, layer in (record.get("layers") or {}).items():
        path = project / "evals" / f"{name}.jsonl"
        if not path.exists() or _digest(path) != layer.get("sha256"):
            mismatched.append(name)
    card.add("exam record", "every eval file matches its recorded digest" if not mismatched
             else f"changed since the build: {', '.join(mismatched)}", not mismatched)


def boot(card: Scorecard, project: Path, timeout: float) -> None:
    """The edge refuses what it should and answers with a request id."""
    service = project / "app" / "service.py"
    if not service.exists():
        card.add("edge", "no app/service.py", None)
        return
    port = _free_port()
    env = {"PATH": os.environ.get("PATH", "/usr/bin"), "PORT": str(port), "AUTH_TOKEN": "scorecard",
           "GRANTED_SCOPES": "x", "LLM_ENDPOINT": "http://127.0.0.1:9",
           "STATE_DIR": str(project / "scorecard-state")}
    if "FINETUNED_MODEL" in service.read_text() or (project / "train").is_dir():
        env["FINETUNED_MODEL"] = "scorecard-adapter"
    proc = subprocess.Popen([sys.executable, "-m", "app.service"], cwd=project, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(int(timeout * 10)):
            if proc.poll() is not None:
                break
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                break
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(0.1)
        if proc.poll() is not None:
            err = (proc.stderr.read() if proc.stderr else "")[-300:]
            card.add("edge: boots", f"exit {proc.returncode}", proc.returncode == 78 and False,
                     err.strip() or "the service exited before answering /health")
            return
        card.add("edge: boots", "answers /health", True)

        def post(body: bytes, token: str | None = "scorecard") -> tuple[int, dict]:
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer " + token
            request = urllib.request.Request(base + "/", data=body, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    return response.status, json.loads(response.read() or b"{}")
            except urllib.error.HTTPError as error:
                try:
                    return error.code, json.loads(error.read() or b"{}")
                except ValueError:
                    return error.code, {}
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
                return 0, {}

        code, body = post(b'"hello"', token=None)
        card.add("edge: identity", f"{code} without a token",
                 code == 401 and "request_id" in body, "no token, no service, with a request id")
        code, body = post(b'{"query": "q", "answer": "forged"}')
        card.add("edge: forged result", f"{code}", code == 422,
                 "a caller cannot hand the pipeline its own answer")
        code, body = post(b'{"query": "q", "principal": {"scopes": ["admin"]}}')
        card.add("edge: forged identity", f"{code}", code == 422)
        code, body = post(b'not json')
        card.add("edge: malformed body", f"{code}", code == 400)
        try:
            with urllib.request.urlopen(base + "/ready", timeout=5) as response:
                ready = json.loads(response.read())
                status = response.status
        except urllib.error.HTTPError as error:
            status, ready = error.code, json.loads(error.read() or b"{}")
        problems = ready.get("problems") or ready.get("ready_problems") or []
        card.add("edge: readiness", f"{status} {'ready' if status == 200 else 'not ready'}"
                 + (f": {'; '.join(map(str, problems))[:120]}" if problems else ""), None,
                 "reported, not judged: readiness depends on the deployment's model and corpus")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def register(card: Scorecard, project: Path) -> None:
    risks = project / "RISKS.md"
    if not risks.exists():
        card.add("risk register", "no RISKS.md", False)
        return
    text = risks.read_text()
    scaffolds = []
    if "## Decided, not yet implemented" in text:
        section = text.split("## Decided, not yet implemented", 1)[1].split("## ", 1)[0]
        scaffolds = re.findall(r"^- `(\w[\w:-]*)`$", section, re.M)
    card.add("risk register: scaffolds", "none" if not scaffolds else ", ".join(scaffolds),
             not scaffolds, "a scaffold raises on use; a green exam cannot include it")
    waived = []
    if "## Gates waived" in text:
        section = text.split("## Gates waived", 1)[1].split("## ", 1)[0]
        waived = re.findall(r"^- \*\*(\w+)\*\*", section, re.M)
    card.add("risk register: gates waived", "none" if not waived else ", ".join(waived), None,
             "reported, not judged: a waiver is the engagement's decision, on the record")
    asserted = len(re.findall(r"asserted, not established", text))
    card.add("risk register: asserted facts", f"{asserted} boundary-bearing fact(s) asserted",
             None, "reported: confirm each with the client before the decisions resting on it "
                   "stand")


def environment(card: Scorecard, project: Path) -> None:
    documented = (project / "deploy" / "env.example")
    if not documented.exists():
        card.add("environment", "no deploy/env.example", False)
        return
    text = documented.read_text()
    read = set()
    for py in project.rglob("*.py"):
        if "scorecard" in py.name:
            continue
        read |= set(re.findall(r"environ(?:\.get)?\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']",
                               py.read_text()))
    read -= {"ANTHROPIC_API_KEY", "PATH", "HF_HUB_OFFLINE"}
    missing = sorted(v for v in read if v not in text)
    card.add("environment", "every variable the code reads is documented" if not missing
             else f"undocumented: {', '.join(missing)}", not missing)


def training(card: Scorecard, project: Path) -> None:
    train = project / "train"
    if not train.is_dir():
        card.add("training path", "none in this build", None)
        return
    records = sorted(train.glob("compare-*.json"))
    if not records:
        card.add("training path", "no comparison run yet", False,
                 "train/README.md: prepare, train, serve, compare")
        return
    latest = json.loads(records[-1].read_text())
    delta = latest.get("delta")
    form = latest.get("form_delta")
    measured = (f"delta {delta:+.1%}" if delta is not None else "no delta") \
        + (f", form {form:+.1%}" if form is not None else "")
    status = (" (quotable)" if latest.get("quotable")
              else f" (not quotable: {latest.get('not_quotable_because')})")
    card.add("training path", measured + status,
             bool(latest.get("quotable")) and (delta or 0) >= 0,
             "a delta is quotable on thirty holdout cases under a calibrated judge")


# --- the document --------------------------------------------------------------


def render(card: Scorecard) -> str:
    lines = [
        "# Scorecard",
        "",
        f"**{card.verdict}.** Measured on `{card.project}`. A property this build cannot "
        "measure is marked n/a, never counted as held.",
        "",
        "| Property | Measured | Holds |",
        "|---|---|---|",
    ]
    for row in card.rows:
        mark = "n/a" if row.holds is None else ("yes" if row.holds else "**no**")
        lines.append(f"| {row.property} | {row.measured} | {mark} |")
    if card.failing:
        lines += ["", "## Not holding", ""]
        for row in card.failing:
            why = f" -- {row.why}" if row.why else ""
            lines.append(f"- **{row.property}**: {row.measured}{why}")
    notes = [r for r in card.rows if r.why and r.holds is not False]
    if notes:
        lines += ["", "## Notes", ""]
        lines += [f"- {r.property}: {r.why}" for r in notes]
    return "\n".join(lines) + "\n"


def score(project: Path, holdout_path: Path | None = None, min_score: float = 0.0,
          timeout: float = 900.0, env: dict | None = None, probe_edge: bool = True) -> Scorecard:
    project = Path(project).resolve()
    card = Scorecard(project=str(project))
    own_tests(card, project, timeout)
    lint(card, project, timeout)
    exam(card, project, timeout, min_score, env)
    holdout(card, project, holdout_path, timeout, env)
    exam_record(card, project)
    if probe_edge:
        boot(card, project, min(timeout, 60.0))
    register(card, project)
    environment(card, project)
    training(card, project)
    (project / "SCORECARD.md").write_text(render(card))
    (project / "scorecard.json").write_text(json.dumps(
        {"project": str(project), "verdict": card.verdict,
         "rows": [asdict(r) for r in card.rows]}, indent=2) + "\n")
    for stray in ("scorecard-harness.json", "scorecard-holdout.json"):
        path = project / stray
        if path.exists():
            path.unlink()
    return card
