"""The fine-tuning data path, emitted beside a finetune decision.

A finetune decision used to ship one method that split a list in memory and
a `run()` that returned the split as if it were an answer. What a client's
engineer needs is the path from verified pairs to a served adapter, with
every step refusing to proceed on data nothing accounts for:

- `train/prepare.py` draws the split -- seeded, stratified by label,
  de-duplicated, unverified pairs set aside -- and records both files'
  digests in a manifest.
- `train/lora.py` trains a LoRA adapter against that record, names the
  adapter by what went into it, and refuses training data whose digest
  changed after it was prepared.
- `train/compare.py` scores the base model and the adapter on the holdout
  the split held back, through the deliverable's own harness, and refuses a
  holdout that is not the one in the manifest.
- `tests/test_train.py` proves the first and third of those model-free, so
  the deliverable's CI covers the data path even where no GPU ever will.

Everything here is plain Python at emission time; the training dependencies
are imported inside `main()` so the recipe reads, lints and plans on a
machine that will never train.
"""

from __future__ import annotations

from pathlib import Path

from fde.architect import Architecture

TRAIN_APPROACHES = {"finetune"}


def trained_components(architecture: Architecture) -> list[str]:
    """The decided components whose approach is fine-tuning, reasoning first."""
    found = [
        component for component, decision in architecture.decisions.decided().items()
        if decision.approach in TRAIN_APPROACHES
    ]
    return sorted(found, key=lambda c: (not c.startswith("reasoning"), c))


def write_training(architecture: Architecture, out: Path) -> bool:
    """Emit the data path. Returns whether anything was written."""
    components = trained_components(architecture)
    if not components:
        return False
    module = components[0].replace(":", "_")
    train = out / "train"
    train.mkdir(parents=True, exist_ok=True)
    (train / "prepare.py").write_text(_PREPARE)
    (train / "lora.py").write_text(_LORA.replace("__COMPONENT__", module))
    (train / "compare.py").write_text(_COMPARE)
    (train / "requirements.txt").write_text(_REQUIREMENTS)
    (train / "README.md").write_text(_README.replace("__COMPONENT__", module))
    tests = out / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_train.py").write_text(_TESTS)
    return True


_PREPARE = r'''"""Prepare a fine-tuning split from verified pairs, and record what it is.

The split is drawn before anything is trained, by seeded content hash within
each label, so two runs on the same pairs agree and a diff between two
manifests means the pairs changed. Exact duplicate inputs are dropped (one
case counted twice is a case the holdout can leak), unverified pairs are set
aside for a verification queue, and both files' digests go in the manifest
so the recipe and the comparison can refuse data that changed under them.

    python train/prepare.py pairs.jsonl --out train/data [--seed 0] [--holdout 0.2]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# Below this many verified pairs an adapter memorises examples rather than
# learning behaviour; the number is a floor, not a target.
MIN_VERIFIED = 500


def load(path: Path) -> list[dict[str, Any]]:
    pairs = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            pair = json.loads(line)
        except ValueError as exc:
            sys.exit(f"{path}:{number}: not JSON ({exc})")
        if not isinstance(pair, dict) or "input" not in pair or "output" not in pair:
            sys.exit(f"{path}:{number}: a pair is an object with input and output")
        pair.setdefault("id", f"line-{number}")
        pairs.append(pair)
    return pairs


def stratum(pair: dict[str, Any]) -> str:
    """What a pair is an example of: its label, else its field set, else its layout."""
    output = pair.get("output")
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        return "fields:" + ",".join(sorted(output))
    return str(pair.get("layout") or "all")


def key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def rank(seed: int, pair_id: str) -> str:
    return hashlib.sha256(f"{seed}:{pair_id}".encode()).hexdigest()


def split(pairs: list[dict[str, Any]], seed: int, holdout: float) -> dict[str, Any]:
    unknown = [p["id"] for p in pairs if p.get("verified") is None]
    if unknown:
        sys.exit(f"{len(unknown)} pairs do not say whether they are verified "
                 f"(first: {unknown[:3]}); unknown is not a third option, because "
                 f"the default becomes a training set")
    verified = [p for p in pairs if p.get("verified")]
    unverified = [p["id"] for p in pairs if not p.get("verified")]

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    duplicates = 0
    for pair in verified:
        k = key(pair["input"])
        if k in seen:
            duplicates += 1
            continue
        seen.add(k)
        unique.append(pair)

    strata: dict[str, list[dict[str, Any]]] = {}
    for pair in unique:
        strata.setdefault(stratum(pair), []).append(pair)

    train: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    counts: dict[str, dict[str, int]] = {}
    for label, members in sorted(strata.items()):
        ordered = sorted(members, key=lambda p: rank(seed, str(p["id"])))
        # A stratum of one trains; there is nothing to hold it out against.
        n_held = round(len(ordered) * holdout) if len(ordered) >= 2 else 0
        n_held = max(n_held, 1) if len(ordered) >= 2 else 0
        held += ordered[:n_held]
        train += ordered[n_held:]
        counts[label] = {"train": len(ordered) - n_held, "holdout": n_held}
    return {"train": train, "holdout": held, "duplicates": duplicates,
            "unverified": unverified, "strata": counts}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pairs", type=Path)
    parser.add_argument("--out", type=Path, default=Path("train/data"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--holdout", type=float, default=0.2)
    parser.add_argument("--min-verified", type=int, default=MIN_VERIFIED,
                        help="refuse below this many verified pairs")
    parser.add_argument("--golden", type=Path, default=Path("evals/golden.jsonl"),
                        help="the shipped golden set; holdout ids found in it are reported")
    args = parser.parse_args(argv)
    if not 0 < args.holdout < 1:
        parser.error("--holdout is a share strictly between 0 and 1")

    pairs = load(args.pairs)
    result = split(pairs, args.seed, args.holdout)
    n_verified = len(result["train"]) + len(result["holdout"]) + result["duplicates"]
    if n_verified < args.min_verified:
        print(f"{n_verified} verified pairs, fewer than {args.min_verified}. "
              f"{len(result['unverified'])} are unverified -- mine those for a "
              f"verification queue rather than training on them", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    train_text = "".join(json.dumps(p, sort_keys=True) + "\n" for p in result["train"])
    holdout_text = "".join(json.dumps(p, sort_keys=True) + "\n" for p in result["holdout"])
    (args.out / "train.jsonl").write_text(train_text)
    (args.out / "holdout.jsonl").write_text(holdout_text)

    golden_ids: set[Any] = set()
    if args.golden.exists():
        golden_ids = {
            json.loads(line).get("id")
            for line in args.golden.read_text().splitlines() if line.strip()
        }
    leaked = sorted(str(p["id"]) for p in result["holdout"] if p["id"] in golden_ids)
    manifest = {
        "seed": args.seed,
        "holdout_share": args.holdout,
        "source": {"path": str(args.pairs), "sha256": digest(args.pairs.read_text())},
        "verified": n_verified,
        "dropped_duplicates": result["duplicates"],
        "unverified_set_aside": len(result["unverified"]),
        "strata": result["strata"],
        "train": {"cases": len(result["train"]), "sha256": digest(train_text)},
        "holdout": {"cases": len(result["holdout"]), "sha256": digest(holdout_text)},
        "holdout_ids_in_golden": leaked,
    }
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"train {len(result['train'])}, holdout {len(result['holdout'])} across "
          f"{len(result['strata'])} strata; {result['duplicates']} duplicate(s) dropped, "
          f"{len(result['unverified'])} unverified set aside")
    if leaked:
        print(f"{len(leaked)} holdout case(s) also sit in {args.golden}: the adapter's "
              f"before/after is measured on the holdout; the shipped exam asks a "
              f"different question", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


_LORA = r'''"""Train a LoRA adapter on the prepared split, and version what it learned from.

The recipe refuses data that changed after it was prepared (the digests in
the manifest are the contract), names the adapter by what went into it (the
training set's digest, the base model, this file, the hyperparameters), and
writes that record beside the weights. Rollback is pointing FINETUNED_MODEL
at the previous version.

    python train/lora.py --dry-run --base-model <id>      # the plan; no GPU, no deps
    python train/lora.py --base-model <hf id or local path> [--data train/data]
                         [--out artifacts/adapters] [--epochs 2] [--merge]

The dependencies in train/requirements.txt are imported inside train() so
this file reads, lints and plans on a machine that will never train.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

HYPERPARAMETERS: dict[str, Any] = {
    "r": 16,
    "alpha": 32,
    "dropout": 0.05,
    "target_modules": ["q_proj", "v_proj"],
    "epochs": 2,
    "learning_rate": 2e-4,
    "max_length": 2048,
    "grad_accumulation": 8,
}


def recipe_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_split(data: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads((data / "manifest.json").read_text())
    train_text = (data / "train.jsonl").read_text()
    if digest(train_text) != manifest["train"]["sha256"]:
        sys.exit(f"{data / 'train.jsonl'} is not the file prepare.py recorded (its sha256 "
                 f"differs) -- run train/prepare.py again rather than training on data "
                 f"nothing accounts for")
    pairs = [json.loads(line) for line in train_text.splitlines() if line.strip()]
    if not pairs:
        sys.exit("the training set is empty")
    return manifest, pairs


def version_of(manifest: dict[str, Any], base_model: str, hyperparameters: dict) -> str:
    material = json.dumps({
        "train_sha256": manifest["train"]["sha256"],
        "base_model": base_model,
        "recipe_sha256": recipe_sha256(),
        "hyperparameters": hyperparameters,
    }, sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()[:12]


def example(pair: dict[str, Any]) -> tuple[str, str]:
    """Prompt and completion, in the exact format the serving component uses.

    Imported from the component so the two cannot drift: an adapter trained
    on one prompt shape and served with another has learned the wrong thing.
    """
    sys.path.insert(0, str(ROOT))
    from app.components.__COMPONENT__ import format_prompt

    prompt = format_prompt(pair["input"], pair.get("evidence") or [])
    output = pair["output"]
    completion = output if isinstance(output, str) else json.dumps(output, sort_keys=True)
    return prompt, completion


def record(manifest: dict[str, Any], base_model: str, hp: dict[str, Any],
           version: str, examples: int) -> dict[str, Any]:
    return {
        "version": version,
        "base_model": base_model,
        "train_sha256": manifest["train"]["sha256"],
        "holdout_sha256": manifest["holdout"]["sha256"],
        "recipe_sha256": recipe_sha256(),
        "hyperparameters": hp,
        "examples": examples,
        "serve": {
            "vllm": f"vllm serve {base_model} --enable-lora "
                    f"--lora-modules {version}=<adapter dir>",
            "env": f"FINETUNED_MODEL={version}",
        },
    }


def train(pairs: list[dict[str, Any]], base_model: str, hp: dict[str, Any],
          out_dir: Path, merge: bool) -> None:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base_model, torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    )
    model = get_peft_model(model, LoraConfig(
        r=hp["r"], lora_alpha=hp["alpha"], lora_dropout=hp["dropout"],
        target_modules=hp["target_modules"], task_type="CAUSAL_LM",
    ))
    model.to(device)
    model.print_trainable_parameters()
    optimizer = torch.optim.AdamW(
        (p for p in model.parameters() if p.requires_grad), lr=hp["learning_rate"],
    )
    model.train()
    step = 0
    last = 0.0
    for epoch in range(hp["epochs"]):
        for pair in pairs:
            prompt, completion = example(pair)
            prompt_ids = tokenizer(prompt)["input_ids"]
            full = tokenizer(
                prompt + " " + completion + tokenizer.eos_token,
                truncation=True, max_length=hp["max_length"],
            )["input_ids"]
            # The prompt is context, not target: its tokens are masked so the
            # adapter learns the completion, not to echo the question.
            masked = min(len(prompt_ids), len(full))
            labels = [-100] * masked + full[masked:]
            loss = model(
                input_ids=torch.tensor([full], device=device),
                labels=torch.tensor([labels], device=device),
            ).loss
            (loss / hp["grad_accumulation"]).backward()
            last = float(loss.item())
            step += 1
            if step % hp["grad_accumulation"] == 0:
                optimizer.step()
                optimizer.zero_grad()
        print(f"epoch {epoch + 1}/{hp['epochs']}: last loss {last:.4f}")
    if step % hp["grad_accumulation"]:
        optimizer.step()
        optimizer.zero_grad()
    model.save_pretrained(str(out_dir / "adapter"))
    tokenizer.save_pretrained(str(out_dir / "adapter"))
    if merge:
        merged = model.merge_and_unload()
        merged.save_pretrained(str(out_dir / "merged"))
        tokenizer.save_pretrained(str(out_dir / "merged"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data", type=Path, default=ROOT / "train" / "data")
    parser.add_argument("--base-model", required=True,
                        help="a Hugging Face id or a local path; the same weights the "
                             "endpoint serves")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts" / "adapters")
    parser.add_argument("--epochs", type=int, default=HYPERPARAMETERS["epochs"])
    parser.add_argument("--merge", action="store_true",
                        help="also save merged weights (for a server without LoRA support)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and the version; train nothing")
    args = parser.parse_args(argv)

    manifest, pairs = load_split(args.data)
    hp = {**HYPERPARAMETERS, "epochs": args.epochs}
    version = version_of(manifest, args.base_model, hp)
    out_dir = args.out / version
    plan = record(manifest, args.base_model, hp, version, len(pairs))
    if args.dry_run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if out_dir.exists():
        print(f"version {version} is already trained at {out_dir}: same data, same base "
              f"model, same recipe -- there is nothing new to learn", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True)
    train(pairs, args.base_model, hp, out_dir, args.merge)
    (out_dir / "adapter-manifest.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n")
    print(f"adapter {version} at {out_dir}")
    print(f"serve:  {plan['serve']['vllm']}")
    print(f"then:   {plan['serve']['env']}  and run train/compare.py before it takes traffic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


_COMPARE = r'''"""Score the base model and the adapter on the holdout the split held back.

Both runs go through the deliverable's own harness, on the holdout that
prepare.py drew before training -- never the shipped golden set, which the
adapter may have trained beside. The comparison refuses a holdout whose
digest is not the one in the manifest, and writes both scores with the
delta beside the adapter record. An adapter that scores below the base
model exits non-zero: it is not served.

    python train/compare.py --before <base model name> --after <adapter name>
                            [--data train/data] [--out train]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(model: str, cases: Path, report: Path) -> dict[str, Any]:
    """One harness run with FINETUNED_MODEL pointed at `model`."""
    env = {**os.environ, "FINETUNED_MODEL": model}
    subprocess.run(
        [sys.executable, "evals/harness.py", "--cases", str(cases),
         "--report", str(report), "--allow-uncalibrated"],
        cwd=ROOT, env=env, check=False,
    )
    if not report.exists():
        sys.exit(f"the harness wrote no report for {model}; its output above says why")
    layer = json.loads(report.read_text())["layers"][0]
    errors = layer.get("errors") or 0
    return {
        "model": model,
        "score": layer.get("score"),
        "cases": layer.get("cases"),
        "errors": len(errors) if isinstance(errors, list) else int(errors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--before", required=True, help="the base model, as the endpoint names it")
    parser.add_argument("--after", required=True, help="the adapter version, as served")
    parser.add_argument("--data", type=Path, default=ROOT / "train" / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "train")
    args = parser.parse_args(argv)

    manifest = json.loads((args.data / "manifest.json").read_text())
    holdout = args.data / "holdout.jsonl"
    if not holdout.exists() or digest(holdout) != manifest["holdout"]["sha256"]:
        print(f"{holdout} is not the holdout prepare.py drew (sha256 differs from the "
              f"manifest) -- a comparison on a changed holdout compares nothing",
              file=sys.stderr)
        return 2
    if not manifest["holdout"]["cases"]:
        print("the holdout is empty; prepare drew nothing to compare on", file=sys.stderr)
        return 2

    before = score(args.before, holdout, args.out / f"harness-{args.before}.json")
    after = score(args.after, holdout, args.out / f"harness-{args.after}.json")
    delta = (None if before["score"] is None or after["score"] is None
             else after["score"] - before["score"])
    result = {
        "holdout_sha256": manifest["holdout"]["sha256"],
        "holdout_cases": manifest["holdout"]["cases"],
        "before": before,
        "after": after,
        "delta": delta,
    }
    (args.out / f"compare-{args.after}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n")

    def show(entry: dict[str, Any]) -> str:
        value = entry["score"]
        return "no score" if value is None else f"{value:.1%}"

    print(f"before ({args.before}): {show(before)} on {before['cases']} cases, "
          f"{before['errors']} error(s)")
    print(f"after  ({args.after}): {show(after)} on {after['cases']} cases, "
          f"{after['errors']} error(s)")
    if delta is None:
        print("no delta: one side produced no score", file=sys.stderr)
        return 1
    print(f"delta  {delta:+.1%}")
    if delta < 0:
        print("the adapter scores below the base model -- do not serve it", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


_REQUIREMENTS = """# Training-time only. The service never imports these.
torch>=2.4
transformers>=4.45
peft>=0.13
"""


_README = """# Training

A fine-tuning decision is a claim: that an adapter, trained on the client's
verified pairs, answers better than the base model does. This directory is
the path that makes the claim checkable, in the order it has to happen.

1. **Split**: `python train/prepare.py <pairs.jsonl> --out train/data`.
   Refuses a pair that does not say whether it is verified, and fewer
   verified pairs than the floor.
2. **Plan**: `python train/lora.py --dry-run --base-model <id>`. Refuses a
   training file whose digest is not the one in the manifest.
3. **Train**: `python train/lora.py --base-model <id>` on a GPU, after
   `pip install -r train/requirements.txt`. Refuses a version that already
   exists: same data, same base, same recipe, nothing new to learn.
4. **Serve**: `vllm serve <id> --enable-lora
   --lora-modules <version>=artifacts/adapters/<version>/adapter`.
5. **Compare**: `python train/compare.py --before <id> --after <version>`.
   Refuses a holdout whose digest changed, and exits non-zero when the
   adapter scores below the base model.
6. **Ship**: set `FINETUNED_MODEL=<version>` in `/etc/app/env` and restart.

## What the split does

`prepare.py` drops exact duplicate inputs (one case counted twice is a case
the holdout can leak), sets unverified pairs aside (they are an asset for a
verification queue, never a training set), stratifies by label so a rare
label is represented on both sides, and draws the holdout by seeded content
hash so two runs agree. The manifest records the seed, the counts per
stratum, and the digest of every file. It also lists holdout ids that also
sit in `evals/golden.jsonl`: the adapter's before/after is measured on the
holdout, and the shipped exam asks a different question.

## What a version is

An adapter is named by the digest of its training set, the base model, the
recipe file and the hyperparameters. Same inputs, same name: `lora.py`
refuses to train a version that exists. Different inputs, different name:
rollback is pointing `FINETUNED_MODEL` at the previous directory.

## What it is for

Behaviour -- tone, house style, output shape. Never facts: anything that
changes belongs in retrieval, where it can be corrected without retraining.
The serving side (`app/components/__COMPONENT__.py`) answers through the
adapter named by `FINETUNED_MODEL` and refuses when none is configured; the
base model does not answer in its place, because that would be the
fine-tuning claim without the fine-tuning.
"""


_TESTS = r'''"""The training data path, model-free.

The split is seeded, stratified, de-duplicated and recorded; the recipe
plans without a GPU or its dependencies; the comparison refuses a holdout
that changed. None of this needs a model, so all of it gates every push.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ("refund", "escalate", "reply")


def pairs_file(tmp_path: Path) -> Path:
    rows = []
    for n in range(12):
        rows.append({"id": f"p{n}", "input": f"complaint number {n} about a fee",
                     "output": LABELS[n % 3], "verified": True})
    rows.append({"id": "dup", "input": "complaint number 1 about a fee",
                 "output": "refund", "verified": True})
    rows.append({"id": "unv", "input": "unchecked complaint", "output": "reply",
                 "verified": False})
    path = tmp_path / "pairs.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def run(*args: str):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)


def prepare(tmp_path: Path, out: str = "data"):
    result = run("train/prepare.py", str(pairs_file(tmp_path)), "--out",
                 str(tmp_path / out), "--min-verified", "4")
    assert result.returncode == 0, result.stderr
    return json.loads((tmp_path / out / "manifest.json").read_text())


def test_the_split_is_recorded_and_deterministic(tmp_path):
    first = prepare(tmp_path, "one")
    second = prepare(tmp_path, "two")
    assert first["train"]["sha256"] == second["train"]["sha256"]
    assert first["holdout"]["sha256"] == second["holdout"]["sha256"]
    assert first["dropped_duplicates"] == 1
    assert first["unverified_set_aside"] == 1
    assert set(first["strata"]) == set(LABELS)
    assert all(s["holdout"] >= 1 for s in first["strata"].values())
    ids = lambda name: {json.loads(line)["id"]  # noqa: E731
                        for line in (tmp_path / "one" / name).read_text().splitlines()}
    assert not ids("train.jsonl") & ids("holdout.jsonl")


def test_too_few_verified_pairs_is_a_refusal_with_the_number(tmp_path):
    result = run("train/prepare.py", str(pairs_file(tmp_path)), "--out", str(tmp_path / "d"))
    assert result.returncode == 2
    assert "13 verified pairs" in result.stderr  # counted before the duplicate is dropped


def test_the_recipe_plans_without_a_gpu(tmp_path):
    prepare(tmp_path)
    result = run("train/lora.py", "--dry-run", "--base-model", "base/model",
                 "--data", str(tmp_path / "data"))
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert len(plan["version"]) == 12
    # twelve unique verified pairs, one held out per label
    assert plan["examples"] == 9


def test_the_recipe_refuses_training_data_that_changed(tmp_path):
    prepare(tmp_path)
    with (tmp_path / "data" / "train.jsonl").open("a") as handle:
        handle.write(json.dumps({"id": "late", "input": "x", "output": "refund"}) + "\n")
    result = run("train/lora.py", "--dry-run", "--base-model", "base/model",
                 "--data", str(tmp_path / "data"))
    assert result.returncode != 0
    assert "not the file prepare.py recorded" in result.stderr


def test_the_comparison_refuses_a_holdout_that_changed(tmp_path):
    prepare(tmp_path)
    with (tmp_path / "data" / "holdout.jsonl").open("a") as handle:
        handle.write(json.dumps({"id": "late", "input": "x", "output": "refund"}) + "\n")
    result = run("train/compare.py", "--before", "base", "--after", "adapter",
                 "--data", str(tmp_path / "data"), "--out", str(tmp_path))
    assert result.returncode == 2
    assert "not the holdout prepare.py drew" in result.stderr
'''
