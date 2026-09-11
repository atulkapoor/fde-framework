"""The worked example's transcript is a contract, not an illustration.

The site tells visitors the example "reproduces its full transcript
exactly". This replays the walkthrough with the real CLI and diffs the
lines the README pins -- so an output change that would silently strand
the transcript fails here, in the same commit, instead of on a
stranger's machine.
"""

import re
from pathlib import Path

from typer.testing import CliRunner

from fde.cli import app

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "invoice-extraction"
runner = CliRunner()


def test_the_walkthrough_reproduces_its_pinned_transcript(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    doc = (EXAMPLE / "README.md").read_text()

    runner.invoke(app, ["start", "acme", "--statement",
                        "Extract structured fields from scanned supplier invoices."])
    frame = runner.invoke(app, ["frame", "engagements/acme",
                                "--registry", str(REPO / "framework"),
                                "--file", str(EXAMPLE / "brief.md")])

    # every pinned frame bullet, byte for byte
    for line in re.findall(r"^#   (- .+)$", doc, re.M):
        assert line in frame.output, f"pinned bullet missing from output: {line}"
    # the follow-ups hint line, exactly as pinned
    pinned_hint = re.search(r"^# (worth asking next.*)$", doc, re.M)
    assert pinned_hint and pinned_hint.group(1) in frame.output

    runner.invoke(app, ["samples", "engagements/acme",
                        "--file", str(EXAMPLE / "pairs.jsonl")])
    status = runner.invoke(app, ["status", "engagements/acme",
                                 "--registry", str(REPO / "framework")])
    assert "blocked by 4" in status.output

    runner.invoke(app, ["baseline", "engagements/acme",
                        "--file", str(EXAMPLE / "baseline.yaml")])
    runner.invoke(app, ["data-access", "engagements/acme",
                        "--note", "read replica returned 14 rows from the invoices table"])
    runner.invoke(app, ["security-review", "engagements/acme",
                        "--note", "client infosec reviewed data paths and egress"])
    runner.invoke(app, ["waive", "engagements/acme", "client_readiness",
                        "--reason", "eval owner named, starts Monday"])

    arch = runner.invoke(app, ["architect", "engagements/acme",
                               "--registry", str(REPO / "framework")])
    fingerprint = re.search(r"# topology on-prem\s+\[([0-9a-f]+)\]", doc)
    assert fingerprint, "example README pins no fingerprint"
    assert fingerprint.group(1) in arch.output, (
        "the pinned fingerprint no longer reproduces -- update the example "
        "README in this same commit"
    )


def _clear_gates(runner_, name, example, extra_waivers=()):
    runner_.invoke(app, ["baseline", name, "--file", str(example / "baseline.yaml")])
    runner_.invoke(app, ["data-access", name, "--note", "rows returned"])
    runner_.invoke(app, ["security-review", name, "--note", "reviewed"])
    runner_.invoke(app, ["waive", name, "client_readiness", "--reason", "named"])
    for gate in extra_waivers:
        runner_.invoke(app, ["waive", name, gate, "--reason", "planned"])


def test_the_policy_qa_walkthrough_reproduces_its_transcript(tmp_path, monkeypatch):
    """Freeform + retrieval + judged inside a boundary: the example that
    shows the recall eval, the offline-evaluability waiver, and an honestly
    undecided component."""
    monkeypatch.chdir(tmp_path)
    example = REPO / "examples" / "policy-qa"
    doc = example.joinpath("README.md").read_text()

    runner.invoke(app, ["start", "helpdesk", "--statement",
                        "Answer support engineers' policy questions from the document base."])
    frame = runner.invoke(app, ["frame", "helpdesk",
                                "--registry", str(REPO / "framework"),
                                "--file", str(example / "brief.md")])
    for line in re.findall(r"^#   (- .+)$", doc, re.M):
        assert line in frame.output, f"pinned bullet missing: {line}"

    runner.invoke(app, ["samples", "helpdesk", "--file", str(example / "pairs.jsonl")])
    status = runner.invoke(app, ["status", "helpdesk",
                                 "--registry", str(REPO / "framework")])
    assert "blocked by 5" in status.output

    _clear_gates(runner, "helpdesk", example,
                 extra_waivers=("offline_evaluability",))
    arch = runner.invoke(app, ["architect", "helpdesk",
                               "--registry", str(REPO / "framework")])
    pinned = re.search(r"# topology on-prem\s+\[([0-9a-f]+)\]", doc)
    assert pinned and pinned.group(1) in arch.output, (
        "policy-qa fingerprint no longer reproduces -- update the example "
        "README in this same commit")
    assert "not decided: perception" in arch.output

    build = runner.invoke(app, ["build", "helpdesk", "--out",
                                str(tmp_path / "project"),
                                "--registry", str(REPO / "framework")])
    assert "evals: 2 golden, 0 edge, 2 adversarial" in build.output
    assert (tmp_path / "project" / "evals" / "retrieval.py").exists()


def test_the_support_triage_walkthrough_reproduces_its_transcript(tmp_path, monkeypatch):
    """Decision + tools: the agent-posture example, where model-planner is
    rejected on the record as not-simplest."""
    monkeypatch.chdir(tmp_path)
    example = REPO / "examples" / "support-triage"
    doc = example.joinpath("README.md").read_text()

    runner.invoke(app, ["start", "triage", "--statement",
                        "Decide each incoming customer complaint: refund, "
                        "escalate, or reply with an explanation."])
    frame = runner.invoke(app, ["frame", "triage",
                                "--registry", str(REPO / "framework"),
                                "--file", str(example / "brief.md")])
    for line in re.findall(r"^#   (- .+)$", doc, re.M):
        assert line in frame.output, f"pinned bullet missing: {line}"

    runner.invoke(app, ["samples", "triage", "--file", str(example / "pairs.jsonl")])
    _clear_gates(runner, "triage", example)
    arch = runner.invoke(app, ["architect", "triage",
                               "--registry", str(REPO / "framework")])
    pinned = re.search(r"# topology customer-vpc\s+\[([0-9a-f]+)\]", doc)
    assert pinned and pinned.group(1) in arch.output, (
        "support-triage fingerprint no longer reproduces -- update the "
        "example README in this same commit")

    build = runner.invoke(app, ["build", "triage", "--out",
                                str(tmp_path / "project"),
                                "--registry", str(REPO / "framework")])
    assert "wrote" in build.output
    architecture_doc = (tmp_path / "project" / "ARCHITECTURE.md").read_text()
    assert "`model-planner` -- optimisation is simpler and applies here" in architecture_doc
    assert "idempotency key" in architecture_doc
