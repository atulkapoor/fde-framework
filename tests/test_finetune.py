"""A fine-tuning decision ships its data path, and its serving side answers
through an adapter or refuses -- never with a data split dressed as an answer.

The sixth audit pass read the finetune emission as a sketch: one method that
split a list in memory, a run() that returned the split, no recipe, no
before/after, no record of what an adapter learned from. Every finding is a
check here before it is a fix.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fde.architect import architect
from fde.emit import emit
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"

HOUSE_STYLE = dict(
    output_shape="freeform", input_format="text", corpus_size=40_000,
    labelled_count=2_000, data_residency="cannot_leave", hosting="on-prem",
    external_systems=0, human_waiting="no", query_pattern="lookup",
)


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


@pytest.fixture(scope="module")
def trained(reg, tmp_path_factory):
    """A freeform build whose reasoning was overridden to finetune -- the
    corpus's own rule is that the prompted model wins the opening move."""
    out = tmp_path_factory.mktemp("finetune")
    profile = Profile()
    profile.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in HOUSE_STYLE.items()])
    architecture = architect(
        profile, reg,
        overrides={"reasoning": {"chosen": "finetune", "because": "house style, measured"}},
    )
    assert architecture.decisions["reasoning"].approach == "finetune"
    emit(architecture, out, registry=reg)
    return out


def run_in(out: Path, code: str, env: dict | None = None):
    return subprocess.run(
        [sys.executable, "-c", code], cwd=out, capture_output=True, text=True,
        timeout=120, env={"PATH": "/usr/bin", **(env or {})},
    )


def test_the_data_path_ships_beside_the_decision(trained):
    for name in ("prepare.py", "lora.py", "compare.py", "README.md", "requirements.txt"):
        assert (trained / "train" / name).exists(), name
    assert (trained / "tests" / "test_train.py").exists()
    readme = (trained / "README.md").read_text()
    assert "`train/`" in readme


def test_the_adapter_is_named_in_the_environment(trained):
    env = (trained / "deploy" / "env.example").read_text()
    assert "FINETUNED_MODEL=" in env
    assert "LLM_ENDPOINT=" in env  # the serving side goes through the one model seam


def test_the_emitted_data_path_passes_its_own_tests(trained):
    """The deliverable's CI runs these model-free: the split is recorded and
    deterministic, the recipe plans without a GPU, changed data is refused."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_train.py"],
        cwd=trained, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout[-2500:] + result.stderr[-800:]


def test_the_data_path_is_lint_clean(trained):
    pytest.importorskip("ruff")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--isolated", "--select", "F,E,W,I,B,UP",
         "--line-length", "100", str(trained)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout[-1500:]


def test_run_refuses_without_an_adapter_instead_of_returning_a_split(trained):
    result = run_in(trained, """
from app.components.reasoning import Reasoning
from app.llm import ModelUnconfigured
try:
    Reasoning().run({"query": "How should we phrase a refund refusal?"})
except ModelUnconfigured as exc:
    assert "FINETUNED_MODEL" in str(exc)
    print("refused")
""")
    assert result.returncode == 0, result.stderr
    assert "refused" in result.stdout


def test_run_answers_through_the_adapter_in_the_training_prompt_shape(trained):
    result = run_in(trained, """
import app.llm
from app.components import reasoning
seen = {}
def fake_complete(prompt, timeout=None, *, model, endpoint=None, stop=None):
    seen["prompt"], seen["model"] = prompt, model
    return " We are sorry, but the fee stands. "
app.llm.complete_raw = fake_complete
out = reasoning.Reasoning().run({"query": "Refuse the refund politely.",
                                 "retrieved": [{"id": "d1", "text": "Fees are final."}]})
assert out["answer"] == "We are sorry, but the fee stands."
assert out["answered_by"] == "v-abc123"
assert seen["model"] == "v-abc123"
assert seen["prompt"] == reasoning.format_prompt("Refuse the refund politely.",
                                                 [{"id": "d1", "text": "Fees are final."}])
assert "=== EVIDENCE ===" in seen["prompt"]
print("ok")
""", env={"FINETUNED_MODEL": "v-abc123"})
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_the_recipe_trains_on_the_prompt_the_component_serves(trained):
    """One prompt shape, imported rather than copied: the recipe's example()
    must produce exactly what format_prompt produces."""
    result = run_in(trained, """
import sys
sys.path.insert(0, "train")
import lora
from app.components.reasoning import format_prompt
prompt, completion = lora.example(
    {"input": "Q?", "output": "A.", "evidence": [{"id": "x", "text": "t"}]})
assert prompt == format_prompt("Q?", [{"id": "x", "text": "t"}])
assert completion == "A."
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_the_adapter_is_served_raw_not_through_a_chat_template(trained):
    """The recipe tokenises raw text; a chat endpoint would wrap the
    prompt in the base model's template. The component posts to
    /v1/completions with the prompt as built."""
    result = run_in(trained, """
import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
seen = {}
class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        seen["path"] = self.path
        seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        body = json.dumps({"choices": [{"text": " Hold the button for ten seconds."}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
server = HTTPServer(("127.0.0.1", 0), Stub)
threading.Thread(target=server.serve_forever, daemon=True).start()
import os
os.environ["LLM_ENDPOINT"] = f"http://127.0.0.1:{server.server_port}"
from app.components import reasoning
out = reasoning.Reasoning(adapter="v7").run({"query": "How do I reset it?"})
assert out["answer"] == "Hold the button for ten seconds."
assert seen["path"] == "/v1/completions", seen
assert seen["body"]["model"] == "v7" and seen["body"]["prompt"].endswith("Answer:")
assert "messages" not in seen["body"]
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_readiness_names_an_adapter_the_endpoint_does_not_serve(trained):
    result = run_in(trained, """
import json, os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
class Models(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"data": [{"id": "base"}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
server = HTTPServer(("127.0.0.1", 0), Models)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ["LLM_ENDPOINT"] = f"http://127.0.0.1:{server.server_port}"
os.environ["LLM_MODEL"] = "base"
os.environ["FINETUNED_MODEL"] = "v7"
from app import service
problems = service._model_problems()
assert problems and "FINETUNED_MODEL 'v7' is not served" in problems[0], problems
os.environ["FINETUNED_MODEL"] = "base"
assert service._model_problems() == []
print("ok")
""", env={"AUTH_TOKEN": "t"})
    assert result.returncode == 0, result.stderr


def test_a_mapper_adapter_reports_what_it_could_not_parse(reg, tmp_path):
    """The representation side: a reply that is not JSON is reported, never
    invented, and a field the reply did not produce is unmapped."""
    out = tmp_path / "mapper"
    profile = Profile()
    profile.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in dict(
        output_shape="structured", input_format="documents", corpus_size=50_000,
        labelled_count=5_000, data_residency="cannot_leave", hosting="on-prem",
        external_systems=0, human_waiting="no", query_pattern="lookup",
    ).items()])
    architecture = architect(
        profile, reg,
        overrides={"representation": {"chosen": "finetune", "because": "layouts vary"}},
    )
    assert architecture.decisions["representation"].approach == "finetune"
    emit(architecture, out, registry=reg)
    assert (out / "train" / "lora.py").exists()
    result = run_in(out, """
import app.llm
from app.components.representation import Representation
replies = iter(['{"total": "12.50", "extra": 1}', "not json at all"])
app.llm.complete_raw = (lambda prompt, timeout=None, *, model, endpoint=None, stop=None:
                        next(replies))
r = Representation(contract=["total", "account"], adapter="v1")
out = r.run({"records": [{"id": "1", "raw": {"Amount": "12.50"}}, {"id": "2", "raw": {}}]})
first, second = out["records"]
assert first["mapped"] == {"total": "12.50"} and first["unmapped"] == ["account"]
assert second["mapped"] == {} and not second["reply_was_json"]
assert out["needs_attention"] == ["1", "2"]
print("ok")
""")
    assert result.returncode == 0, result.stderr
    manifest = json.loads((out / "evals" / "manifest.json").read_text())
    assert manifest["holdout"] is None  # no pairs, no holdout: recorded as such


def test_a_completion_stops_at_the_next_question(trained):
    """A base model that has not learned to stop continues with the next
    question it imagines; the stop is sent to the server and applied on
    the way back."""
    result = run_in(trained, """
import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
seen = {}
class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        text = (" Hold the dial for ten seconds."
                "\\nQuestion: What colour is the ring?\\nAnswer: amber")
        body = json.dumps({"choices": [{"text": text}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
server = HTTPServer(("127.0.0.1", 0), Stub)
threading.Thread(target=server.serve_forever, daemon=True).start()
import os
os.environ["LLM_ENDPOINT"] = f"http://127.0.0.1:{server.server_port}"
from app.components import reasoning
out = reasoning.Reasoning(adapter="v7").run({"query": "How do I reset it?"})
assert out["answer"] == "Hold the dial for ten seconds.", out["answer"]
assert "\\nQuestion:" in seen["body"]["stop"], seen["body"]
print("ok")
""")
    assert result.returncode == 0, result.stderr


def test_a_comparison_with_no_signal_is_not_a_pass(trained, tmp_path):
    """Zero against zero once exited green as 'not worse'."""
    out = tmp_path / "nosignal"
    shutil.copytree(trained, out, ignore=shutil.ignore_patterns("__pycache__"))
    (out / "evals" / "harness.py").write_text(
        "import argparse, json\n"
        "p = argparse.ArgumentParser()\n"
        "for flag in ('--cases', '--report'):\n"
        "    p.add_argument(flag)\n"
        "p.add_argument('--allow-uncalibrated', action='store_true')\n"
        "a = p.parse_args()\n"
        "json.dump({'layers': [{'layer': 'holdout', 'cases': 6, 'score': 0.0, 'errors': 0}]},"
        " open(a.report, 'w'))\n"
    )
    run_prep = subprocess.run(
        [sys.executable, "train/prepare.py", str(_pairs(tmp_path)), "--out", "train/data",
         "--min-verified", "1"], cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "CORPUS_DIR": str(_corpus(tmp_path))},
    )
    assert run_prep.returncode == 0, run_prep.stderr
    result = subprocess.run(
        [sys.executable, "train/compare.py", "--before", "base", "--after", "v1",
         "--data", "train/data", "--out", "train"],
        cwd=out, capture_output=True, text=True, env={"PATH": "/usr/bin"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "no signal" in result.stderr


def _pairs(tmp_path: Path) -> Path:
    path = tmp_path / "pairs.jsonl"
    path.write_text("".join(json.dumps(
        {"id": f"q{i}", "input": f"How do I reset device {i}?",
         "output": f"Short answer: hold the button on device {i}.", "verified": True}) + "\n"
        for i in range(6)))
    return path


def _corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    root.mkdir(exist_ok=True)
    (root / "reset.txt").write_text("To reset a device, hold its button for ten seconds.")
    return root


def test_a_delta_on_too_few_cases_is_not_quotable(trained, tmp_path):
    """Six cases cannot tell one score from another; the record says so,
    and a delta is written only when asked for as a smoke test."""
    out = tmp_path / "small"
    shutil.copytree(trained, out, ignore=shutil.ignore_patterns("__pycache__"))
    (out / "evals" / "harness.py").write_text(
        "import argparse, json\n"
        "p = argparse.ArgumentParser()\n"
        "for flag in ('--cases', '--report'):\n"
        "    p.add_argument(flag)\n"
        "p.add_argument('--allow-uncalibrated', action='store_true')\n"
        "a = p.parse_args()\n"
        "json.dump({'judged': True, 'calibration': {'calibrated': False},"
        " 'layers': [{'layer': 'holdout', 'cases': 3, 'score': 0.5, 'form': 1.0,"
        " 'errors': 0}]}, open(a.report, 'w'))\n"
    )
    prep = subprocess.run(
        [sys.executable, "train/prepare.py", str(_pairs(tmp_path)), "--out", "train/data",
         "--min-verified", "1", "--retrieve"], cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "CORPUS_DIR": str(_corpus(tmp_path))},
    )
    assert prep.returncode == 0, prep.stderr
    argv = [sys.executable, "train/compare.py", "--before", "base", "--after", "v1",
            "--data", "train/data", "--out", "train"]
    refused = subprocess.run(argv, cwd=out, capture_output=True, text=True,
                             env={"PATH": "/usr/bin"})
    assert refused.returncode == 1 and "fewer than 30 holdout cases" in refused.stderr
    allowed = subprocess.run([*argv, "--allow-small"], cwd=out, capture_output=True,
                             text=True, env={"PATH": "/usr/bin"})
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr
    record = json.loads((out / "train" / "compare-v1.json").read_text())
    assert record["quotable"] is False and "n=" in record["not_quotable_because"]
    assert record["after"]["form"] == 1.0 and record["form_delta"] == 0.0
    assert "not quotable" in allowed.stderr


def test_a_fine_tune_build_without_an_adapter_refuses_to_boot(trained, tmp_path):
    """A bogus adapter name refused the boot; an absent one booted green
    and answered 503 to every request."""
    result = subprocess.run(
        [sys.executable, "-m", "app.service"], cwd=trained, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "PORT": "18993", "AUTH_TOKEN": "t",
             "LLM_ENDPOINT": "http://127.0.0.1:9", "STATE_DIR": str(tmp_path / "s")},
        timeout=60,
    )
    assert result.returncode == 78, result.stderr[-500:]
    assert "FINETUNED_MODEL unset" in result.stderr


def test_the_harness_measures_form_beside_the_judge(reg, tmp_path):
    """A fine-tune teaches form; a judge grades content. When the verified
    answers share an opening, the harness scores how many answers open
    that way, and the comparison carries it."""
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("".join(json.dumps(
        {"id": f"q{i}", "input": f"How do I reset device {i}?", "verified": True,
         "output": f"Short answer: hold the button on device {i}. Steps: 1. Hold it."})
        + "\n" for i in range(12)))
    out = tmp_path / "styled"
    profile = Profile()
    profile.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in HOUSE_STYLE.items()])
    architecture = architect(
        profile, reg, overrides={"reasoning": {"chosen": "finetune", "because": "style"}})
    emit(architecture, out, registry=reg, pairs_path=pairs)
    harness = (out / "evals" / "harness.py").read_text()
    assert "FORM = 'Short answer:'" in harness, "no form marker"
    result = run_in(out, """
import importlib.util
spec = importlib.util.spec_from_file_location("h", "evals/harness.py")
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
h.JUDGED = False  # the form metric is model-free; the judge is not under test here
cases = [{"id": "a", "input": "q", "output": "Short answer: yes. Steps: 1."},
         {"id": "b", "input": "q", "output": "Short answer: no. Steps: 1."}]
answers = iter(["short answer: yes.", "No idea."])
layer = h.run_layer("holdout", cases, lambda text: next(answers))
assert layer["form"] == 0.5, layer["form"]
print("ok")
""")
    assert result.returncode == 0, result.stderr

