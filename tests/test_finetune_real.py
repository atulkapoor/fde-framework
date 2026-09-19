"""The recipe against real weights: skipped unless FDE_TRAIN_PYTHON names an
interpreter with torch, transformers and peft.

The merge path once trained one epoch and saved an adapter whose B
matrices were exactly zero under a versioned name -- a defect no model-free
test can see. This one builds a tiny random causal LM (no download), runs
the emitted recipe plain and with --merge, and reads the tensors back.

    FDE_TRAIN_PYTHON=/path/to/venv/bin/python pytest -q tests/test_finetune_real.py
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

import pytest

from fde.architect import architect
from fde.emit import emit
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"
# A command prefix, so a native interpreter can be forced on a machine
# whose test process runs under Rosetta: FDE_TRAIN_PYTHON="arch -arm64 /path/python".
TRAIN_PYTHON = os.environ.get("FDE_TRAIN_PYTHON")
TRAIN = shlex.split(TRAIN_PYTHON) if TRAIN_PYTHON else []

pytestmark = pytest.mark.skipif(
    not TRAIN_PYTHON, reason="FDE_TRAIN_PYTHON not set: no torch/peft interpreter")

TINY_MODEL = """
import sys
from transformers import GPT2Config, GPT2LMHeadModel, AutoTokenizer
out = sys.argv[1]
tok = AutoTokenizer.from_pretrained("gpt2")
tok.save_pretrained(out)
cfg = GPT2Config(n_layer=2, n_head=2, n_embd=32, vocab_size=tok.vocab_size, n_positions=256)
GPT2LMHeadModel(cfg).save_pretrained(out)
print("tiny model at", out)
"""


def train_run(python: list[str], project: Path, data: Path, base: Path, out: Path, *extra: str):
    return subprocess.run(
        [*python, "train/lora.py", "--base-model", str(base), "--data", str(data),
         "--out", str(out), "--epochs", "5", "--grad-accumulation", "1",
         "--learning-rate", "5e-3", *extra],
        cwd=project, capture_output=True, text=True, timeout=900,
        env={**os.environ, "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE", "0")},
    )


def test_merge_trains_every_epoch_and_saves_a_real_adapter(tmp_path):
    reg = load_registry(FRAMEWORK)
    project = tmp_path / "project"
    profile = Profile()
    profile.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in dict(
        output_shape="freeform", input_format="text", corpus_size=1_000, labelled_count=2_000,
        data_residency="cannot_leave", hosting="on-prem", external_systems=0,
        human_waiting="no", query_pattern="lookup").items()])
    emit(architect(profile, reg, overrides={"reasoning": {"chosen": "finetune",
                                                          "because": "style"}}),
         project, registry=reg)
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("".join(json.dumps(
        {"id": f"q{i}", "input": f"Reset device {i}?",
         "output": f"Short answer: hold button {i}.", "verified": True}) + "\n"
        for i in range(16)))
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "reset.txt").write_text("To reset a device hold its button for ten seconds.")
    prep = subprocess.run(
        [*TRAIN, "train/prepare.py", str(pairs), "--out", str(tmp_path / "data"),
         "--min-verified", "1", "--retrieve", "--holdout", "0.25"],
        cwd=project, capture_output=True, text=True, env={**os.environ, "CORPUS_DIR": str(corpus)},
    )
    assert prep.returncode == 0, prep.stderr
    base = tmp_path / "tiny"
    made = subprocess.run([*TRAIN, "-c", TINY_MODEL, str(base)],
                          capture_output=True, text=True, timeout=600)
    assert made.returncode == 0, made.stderr[-800:]

    plain = train_run(TRAIN, project, tmp_path / "data", base, tmp_path / "plain")
    assert plain.returncode == 0, plain.stderr[-1500:]
    merged = train_run(TRAIN, project, tmp_path / "data", base, tmp_path / "merged",
                       "--merge")
    assert merged.returncode == 0, merged.stderr[-1500:]

    def history(out: Path) -> list[float]:
        version = next(p for p in out.iterdir() if p.is_dir())
        record = json.loads((version / "adapter-manifest.json").read_text())
        return [h["train_loss"] for h in record["training"]["history"]], version

    plain_losses, _ = history(tmp_path / "plain")
    merged_losses, merged_version = history(tmp_path / "merged")
    # The merge path trains exactly what the plain path trains: same seed,
    # same losses epoch for epoch. Merging inside the loop once froze the
    # optimizer after the first epoch.
    assert merged_losses == plain_losses, (merged_losses, plain_losses)
    assert len(plain_losses) >= 2 and plain_losses[-1] < plain_losses[0], plain_losses
    assert (merged_version / "merged" / "config.json").exists()
    probe = subprocess.run([*TRAIN, "-c", f"""
from safetensors.torch import load_file
import glob
adapter_dir = {str(merged_version / 'adapter')!r}
tensors = load_file(glob.glob(adapter_dir + '/adapter_model.safetensors')[0])
b = [v.abs().max().item() for k, v in tensors.items() if 'lora_B' in k]
assert b and max(b) > 0, b
print('lora_B max', max(b))
"""], capture_output=True, text=True, timeout=300)
    assert probe.returncode == 0, probe.stderr[-800:]
