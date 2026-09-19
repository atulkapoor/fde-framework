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
- `train/serve.py` puts the base model and an adapter behind the same wire
  shape production uses (`/v1/models`, `/v1/completions`), in-process, so
  the comparison can run on the machine that trained.
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
    with_evidence = "retrieval" in architecture.decisions.decided()
    train = out / "train"
    train.mkdir(parents=True, exist_ok=True)
    (train / "prepare.py").write_text(_PREPARE)
    (train / "lora.py").write_text(
        _LORA.replace("__COMPONENT__", module)
             .replace("__WITH_EVIDENCE__", "True" if with_evidence else "False"))
    (train / "compare.py").write_text(_COMPARE)
    (train / "serve.py").write_text(_SERVE)
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
                            [--retrieve]   # attach the retrieval layer's evidence

Where the build serves the adapter with evidence blocks (retrieval in front
of reasoning), the adapter must train on that shape: --retrieve runs each
input through the deliverable's own retriever over CORPUS_DIR and stores the
hits on the pair, so prompt and training example are the same bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

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


def is_label(output: Any) -> bool:
    if isinstance(output, str):
        return True
    return (isinstance(output, dict) and len(output) == 1
            and isinstance(next(iter(output.values())), str))


def stratum(pair: dict[str, Any]) -> str:
    """What a pair is an example of: its label, else its layout."""
    output = pair.get("output")
    if isinstance(output, dict) and len(output) == 1:
        output = next(iter(output.values()))
    if isinstance(output, str):
        return output
    return str(pair.get("layout") or "all")


def strata_of(pairs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """By label when the outputs are a label set; otherwise one stratum.
    Six hundred freeform answers are six hundred strata of one, and a
    split by them once held nothing out."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for pair in pairs:
        groups.setdefault(stratum(pair), []).append(pair)
    few = 1 < len(groups) <= min(20, max(1, len(pairs) // 2))
    if few and all(is_label(p.get("output")) for p in pairs):
        return groups
    return {"all": pairs}


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

    strata = strata_of(unique)

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
    # The recipe shuffles per epoch; the file is still written in a
    # seeded order rather than label by label, so a reader of the file
    # sees the mix the adapter will.
    train.sort(key=lambda p: rank(seed + 1, str(p["id"])))
    return {"train": train, "holdout": held, "duplicates": duplicates,
            "unverified": unverified, "strata": counts}


def attach_evidence(pairs: list[dict[str, Any]]) -> int:
    """Each input through the deliverable's own retriever, hits stored on
    the pair. Returns the corpus size the hits came from."""
    sys.path.insert(0, str(ROOT))
    from app import pipeline

    retriever = getattr(pipeline, "RETRIEVER", None)
    if retriever is None:
        sys.exit("this build has no retrieval layer; there is no evidence to attach")
    documents = pipeline.load_corpus()
    if not documents:
        sys.exit("CORPUS_DIR holds no documents: the adapter would train on empty "
                 "evidence blocks and serve with full ones")
    for pair in pairs:
        query = pair["input"] if isinstance(pair["input"], str) else json.dumps(pair["input"])
        # The same call the request path makes, with the same default k:
        # training on eight blocks and serving five is a prompt the adapter
        # never saw. A caller's own `k` changes the served shape; the
        # README says so.
        hits = retriever.run({"query": query}).get("retrieved") or []
        pair["evidence"] = [{"id": h.get("id"), "text": h.get("text", "")} for h in hits]
    return documents


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
    parser.add_argument("--retrieve", action="store_true",
                        help="attach the retrieval layer's top hits from CORPUS_DIR to "
                             "each pair, so the adapter trains on the shape it serves")
    args = parser.parse_args(argv)
    if not 0 < args.holdout < 1:
        parser.error("--holdout is a share strictly between 0 and 1")

    pairs = load(args.pairs)
    corpus = attach_evidence(pairs) if args.retrieve else 0
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
        # The floor this split was accepted against. A run at a lower floor
        # is a smoke test and the artefacts say so; it once ran at 10 against
        # a documented 500 and nothing on disk could tell.
        "min_verified": args.min_verified,
        "floor_overridden": args.min_verified != MIN_VERIFIED,
        "dropped_duplicates": result["duplicates"],
        "unverified_set_aside": len(result["unverified"]),
        "strata": result["strata"],
        "train": {"cases": len(result["train"]), "sha256": digest(train_text)},
        "holdout": {"cases": len(result["holdout"]), "sha256": digest(holdout_text)},
        "holdout_ids_in_golden": leaked,
        # What the prompts will look like: with evidence blocks from the
        # corpus, or bare. The recipe refuses a shape the build does not serve.
        "evidence": {"source": "retrieved", "corpus_documents": corpus,
                     "k": "the pipeline's default"}
        if args.retrieve else {"source": "none"},
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
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Whether the deliverable serves the adapter with retrieved evidence in the
# prompt (retrieval in front of reasoning). Training pairs must then carry
# evidence -- prepare.py --retrieve -- or the adapter learns a bare shape
# it will never be served in.
SERVES_WITH_EVIDENCE = __WITH_EVIDENCE__

# Below this many optimizer steps a run is a smoke test, not a fine-tune.
MIN_OPTIMIZER_STEPS = 50
# prepare.py's floor, quoted here so the note above can name it.
MIN_VERIFIED_NOTE = 500

HYPERPARAMETERS: dict[str, Any] = {
    "seed": 0,
    "r": 16,
    "alpha": 32,
    "dropout": 0.05,
    # None lets peft pick the attention projections for the architecture
    # (q_proj/v_proj on Llama-style models, c_attn on GPT-2); a hard-coded
    # Llama list once refused every other family. Override with
    # --target-modules when the base model is not in peft's table.
    "target_modules": None,
    "epochs": 3,
    "learning_rate": 2e-4,
    "max_length": 2048,
    # Examples per forward pass, and passes per optimizer step: the
    # effective batch is their product (32 by default).
    "batch_size": 4,
    "grad_accumulation": 8,
    # Linear warm-up over the first tenth of the steps, cosine decay to a
    # tenth of the peak over the rest; gradients clipped at norm 1.0.
    "warmup_share": 0.1,
    "final_lr_share": 0.1,
    "max_grad_norm": 1.0,
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
    if not manifest.get("holdout", {}).get("cases"):
        sys.exit("the holdout is empty: nothing would measure this adapter before it "
                 "took traffic -- prepare with more pairs or a smaller --holdout share")
    if SERVES_WITH_EVIDENCE and manifest.get("evidence", {}).get("source") != "retrieved":
        sys.exit("this build serves the adapter with evidence blocks (retrieval in front "
                 "of reasoning) and these pairs carry none -- prepare with --retrieve "
                 "(CORPUS_DIR set) so the adapter trains on the shape it is served in")
    return manifest, pairs


def load_holdout(data: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (data / "holdout.jsonl").read_text().splitlines()
            if line.strip()]


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
        "verified_pairs": manifest.get("verified"),
        "min_verified": manifest.get("min_verified"),
        "floor_overridden": bool(manifest.get("floor_overridden")),
        "evidence": manifest.get("evidence"),
        "serve": {
            "vllm": f"vllm serve {base_model} --enable-lora "
                    f"--lora-modules {version}=<adapter dir>",
            "env": f"FINETUNED_MODEL={version}",
        },
    }


def optimizer_steps(examples: int, hp: dict[str, Any]) -> int:
    """How many times the weights move: passes per epoch (examples over the
    batch size, rounded up) times epochs, over the accumulation."""
    passes = -(-examples // hp["batch_size"]) * hp["epochs"]
    return max(1, -(-passes // hp["grad_accumulation"]))


def lr_factor(step: int, total: int, hp: dict[str, Any]) -> float:
    """Linear warm-up, then cosine decay to a share of the peak."""
    warmup = max(1, int(total * hp["warmup_share"]))
    if step < warmup:
        return (step + 1) / warmup
    progress = min(1.0, (step - warmup) / max(1, total - warmup))
    floor = hp["final_lr_share"]
    return floor + (1 - floor) * 0.5 * (1 + math.cos(math.pi * progress))


def encode(tokenizer: Any, pair: dict[str, Any], max_length: int) -> tuple[list[int], list[int]]:
    """Token ids and labels for one example. Prompt and completion are
    tokenised separately and joined as ids, so the mask boundary is exact
    rather than guessed from a re-tokenised concatenation; the prompt is
    truncated from the LEFT so the completion is always present, and an
    example with no completion tokens is refused rather than trained on
    as a NaN."""
    prompt, completion = example(pair)
    prompt_ids = tokenizer(prompt, add_special_tokens=True)["input_ids"]
    completion_ids = tokenizer(" " + completion, add_special_tokens=False)["input_ids"]
    completion_ids.append(tokenizer.eos_token_id)
    if len(completion_ids) >= max_length:
        raise ValueError(f"completion of {pair.get('id')} alone exceeds max_length")
    room = max_length - len(completion_ids)
    prompt_ids = prompt_ids[-room:]
    ids = prompt_ids + completion_ids
    labels = [-100] * len(prompt_ids) + completion_ids
    assert any(label != -100 for label in labels)
    return ids, labels


def train(pairs: list[dict[str, Any]], holdout: list[dict[str, Any]], base_model: str,
          hp: dict[str, Any], out_dir: Path, merge: bool,
          gradient_checkpointing: bool = False) -> dict[str, Any]:
    import random

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(hp["seed"])
    shuffle = random.Random(hp["seed"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base_model, torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    )
    if gradient_checkpointing:
        model.gradient_checkpointing_enable()
    model = get_peft_model(model, LoraConfig(
        r=hp["r"], lora_alpha=hp["alpha"], lora_dropout=hp["dropout"],
        target_modules=hp["target_modules"], task_type="CAUSAL_LM",
    ))
    # What was actually adapted, on the record, whichever way it was chosen.
    targeted = model.peft_config["default"].target_modules
    hp["target_modules"] = sorted(targeted) if isinstance(targeted, (set, list)) else targeted
    model.to(device)
    model.print_trainable_parameters()
    optimizer = torch.optim.AdamW(
        (p for p in model.parameters() if p.requires_grad), lr=hp["learning_rate"],
    )
    encoded = [encode(tokenizer, pair, hp["max_length"]) for pair in pairs]
    held = [encode(tokenizer, pair, hp["max_length"]) for pair in holdout]
    pad = tokenizer.pad_token_id
    total_steps = optimizer_steps(len(encoded), hp)
    schedule = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda s: lr_factor(s, total_steps, hp))

    def batch_loss(rows: list[tuple[list[int], list[int]]]) -> Any:
        """One forward pass over a padded batch; padding is masked out of
        attention and out of the loss."""
        width = max(len(ids) for ids, _ in rows)
        input_ids = torch.tensor(
            [ids + [pad] * (width - len(ids)) for ids, _ in rows], device=device)
        attention = torch.tensor(
            [[1] * len(ids) + [0] * (width - len(ids)) for ids, _ in rows], device=device)
        labels = torch.tensor(
            [lab + [-100] * (width - len(lab)) for _, lab in rows], device=device)
        return model(input_ids=input_ids, attention_mask=attention, labels=labels).loss

    def holdout_loss() -> float:
        model.eval()
        with torch.no_grad():
            total = sum(float(batch_loss(held[i:i + hp["batch_size"]]).item())
                        * len(held[i:i + hp["batch_size"]])
                        for i in range(0, len(held), hp["batch_size"]))
        model.train()
        return total / len(held)

    history: list[dict[str, float]] = []
    best = float("inf")
    passes = 0
    model.train()
    for epoch in range(hp["epochs"]):
        order = list(range(len(encoded)))
        shuffle.shuffle(order)  # label-grouped order once made every step single-label
        running = 0.0
        batches = [order[i:i + hp["batch_size"]] for i in range(0, len(order), hp["batch_size"])]
        for rows in batches:
            loss = batch_loss([encoded[n] for n in rows])
            (loss / hp["grad_accumulation"]).backward()
            running += float(loss.item()) * len(rows)
            passes += 1
            if passes % hp["grad_accumulation"] == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), hp["max_grad_norm"])
                optimizer.step()
                schedule.step()
                optimizer.zero_grad()
        if passes % hp["grad_accumulation"]:
            torch.nn.utils.clip_grad_norm_(model.parameters(), hp["max_grad_norm"])
            optimizer.step()
            schedule.step()
            optimizer.zero_grad()
        evaluated = holdout_loss()
        history.append({"epoch": epoch + 1, "train_loss": running / len(encoded),
                        "holdout_loss": evaluated})
        print(f"epoch {epoch + 1}/{hp['epochs']}: train loss {running / len(encoded):.4f}, "
              f"holdout loss {evaluated:.4f}")
        if evaluated < best:
            # The adapter on disk is always the best epoch by holdout loss.
            best = evaluated
            model.save_pretrained(str(out_dir / "adapter"))
            tokenizer.save_pretrained(str(out_dir / "adapter"))
        else:
            print("holdout loss did not fall: stopping, keeping the previous epoch's adapter")
            break
    if merge:
        # Merged AFTER training, from the best adapter on disk onto a fresh
        # base. Merging inside the loop once left the optimizer holding the
        # old LoRA tensors: every later epoch trained nothing, and the saved
        # adapter's B matrices were exactly zero under a versioned name.
        from peft import PeftModel

        fresh = AutoModelForCausalLM.from_pretrained(
            base_model, torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        )
        merged = PeftModel.from_pretrained(fresh, str(out_dir / "adapter")).merge_and_unload()
        merged.save_pretrained(str(out_dir / "merged"))
        tokenizer.save_pretrained(str(out_dir / "merged"))
    return {
        "history": history,
        "best_holdout_loss": best,
        "environment": environment(model, device),
    }


def environment(model: Any, device: str) -> dict[str, Any]:
    """What the numbers above were produced on: the same version trained
    in bf16 on a GPU will not reproduce CPU fp32 losses, and a manifest
    that cannot say which is which cannot say what it recorded."""
    import peft
    import torch
    import transformers

    return {
        "device": device,
        "dtype": str(next(model.parameters()).dtype),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "peft": peft.__version__,
        "base_model_revision": getattr(getattr(model, "config", None), "_commit_hash", None),
    }


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
    parser.add_argument("--seed", type=int, default=HYPERPARAMETERS["seed"])
    parser.add_argument("--batch-size", type=int, default=HYPERPARAMETERS["batch_size"],
                        help="examples per forward pass")
    parser.add_argument("--target-modules", default=None,
                        help="comma-separated module names to adapt; default is peft's "
                             "choice for the architecture")
    parser.add_argument("--grad-accumulation", type=int,
                        default=HYPERPARAMETERS["grad_accumulation"],
                        help="forward passes per optimizer step; lower it on a small corpus")
    parser.add_argument("--learning-rate", type=float, default=HYPERPARAMETERS["learning_rate"])
    parser.add_argument("--gradient-checkpointing", action="store_true",
                        help="trade compute for memory on a small card")
    args = parser.parse_args(argv)

    manifest, pairs = load_split(args.data)
    hp = {**HYPERPARAMETERS, "epochs": args.epochs, "seed": args.seed,
          "batch_size": args.batch_size, "grad_accumulation": args.grad_accumulation,
          "learning_rate": args.learning_rate,
          "target_modules": ([m.strip() for m in args.target_modules.split(",") if m.strip()]
                             if args.target_modules else None)}
    version = version_of(manifest, args.base_model, hp)
    out_dir = args.out / version
    plan = record(manifest, args.base_model, hp, version, len(pairs))
    # How many times the weights actually move. Eighteen pairs, three
    # epochs and an accumulation of eight is seven steps: a run that
    # cannot teach a style, and it should say so before the GPU is booked.
    steps = optimizer_steps(len(pairs), hp)
    plan["optimizer_steps"] = steps
    plan["schedule"] = (f"AdamW, linear warm-up over {max(1, int(steps * hp['warmup_share']))} "
                        f"step(s), cosine decay to {hp['final_lr_share']:.0%} of "
                        f"{hp['learning_rate']}, gradients clipped at {hp['max_grad_norm']}, "
                        f"effective batch {hp['batch_size'] * hp['grad_accumulation']}")
    if manifest.get("floor_overridden"):
        print(f"note: the split was accepted at --min-verified {manifest.get('min_verified')} "
              f"({manifest.get('verified')} verified pairs) below the recipe's floor of "
              f"{MIN_VERIFIED_NOTE}: this adapter is a smoke test of the path, not a "
              f"fine-tune, and its manifest says so", file=sys.stderr)
    if steps < MIN_OPTIMIZER_STEPS:
        print(f"note: {steps} optimizer steps ({len(pairs)} examples x {hp['epochs']} epochs "
              f"/ batch {hp['batch_size']} / accumulation {hp['grad_accumulation']}) -- fewer "
              f"than {MIN_OPTIMIZER_STEPS} barely moves a model; lower --grad-accumulation "
              f"or --batch-size, or add --epochs", file=sys.stderr)
    if args.dry_run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if out_dir.exists():
        print(f"version {version} is already trained at {out_dir}: same data, same base "
              f"model, same recipe -- there is nothing new to learn", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True)
    outcome = train(pairs, load_holdout(args.data), args.base_model, hp, out_dir,
                    args.merge, args.gradient_checkpointing)
    plan["training"] = outcome
    plan["hyperparameters"]["target_modules"] = hp["target_modules"]
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
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(name: str) -> str:
    """A model name as a file name: 'org/model' once became a directory."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "model"


# Fewer holdout cases than this and no delta is quotable: the acceptance
# protocol's own sample floor. Wilson 95% on 1/6 is [0.03, 0.56].
MIN_HOLDOUT_CASES = 30


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
    written = json.loads(report.read_text())
    layer = written["layers"][0]
    errors = layer.get("errors") or 0
    return {
        "model": model,
        "score": layer.get("score"),
        # The form metric, where the harness has one: the share of answers
        # that open the way the verified answers open. A fine-tune teaches
        # form; a judge grades content; one number cannot carry both.
        "form": layer.get("form"),
        "cases": layer.get("cases"),
        "errors": len(errors) if isinstance(errors, list) else int(errors),
        "judge_calibrated": bool((written.get("calibration") or {}).get("calibrated")),
        "judged": bool(written.get("judged")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--before", required=True, help="the base model, as the endpoint names it")
    parser.add_argument("--after", required=True, help="the adapter version, as served")
    parser.add_argument("--data", type=Path, default=ROOT / "train" / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "train")
    parser.add_argument("--allow-small", action="store_true",
                        help=f"write a delta on fewer than {MIN_HOLDOUT_CASES} holdout cases "
                             f"-- a smoke test of the path, marked as such")
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

    args.out.mkdir(parents=True, exist_ok=True)
    before = score(args.before, holdout, args.out / f"harness-{slug(args.before)}.json")
    after = score(args.after, holdout, args.out / f"harness-{slug(args.after)}.json")
    if before["errors"] or after["errors"]:
        # Both sides erroring on every case once produced delta +0.0% and
        # a green exit: the comparison measured nothing.
        print(f"errors: before {before['errors']}, after {after['errors']} -- the harness "
              f"could not score every case, so this comparison measured nothing; "
              f"fix the endpoint or the adapter before reading a delta", file=sys.stderr)
        return 2
    if not before["score"] and not after["score"]:
        # Zero against zero is not "not worse"; it is a judge, a prompt or
        # a model that produced no signal, and a green exit here once read
        # as an adapter cleared to serve.
        print("no signal: neither the base model nor the adapter scored a single case; "
              "check the served prompt, the stop sequences and the judge before "
              "reading anything into this", file=sys.stderr)
        return 1
    n = manifest["holdout"]["cases"]
    if n < MIN_HOLDOUT_CASES and not args.allow_small:
        print(f"n={n}: fewer than {MIN_HOLDOUT_CASES} holdout cases cannot tell one score "
              f"from another; no delta is quotable. Prepare more pairs, or --allow-small "
              f"for a smoke test of the path", file=sys.stderr)
        return 1
    delta = (None if before["score"] is None or after["score"] is None
             else after["score"] - before["score"])
    form_delta = (None if before.get("form") is None or after.get("form") is None
                  else after["form"] - before["form"])
    quotable = n >= MIN_HOLDOUT_CASES and (not after["judged"] or after["judge_calibrated"])
    result = {
        "holdout_sha256": manifest["holdout"]["sha256"],
        "holdout_cases": n,
        "before": before,
        "after": after,
        "delta": delta,
        "form_delta": form_delta,
        # A delta is quotable only on enough cases under a calibrated judge
        # (or no judge at all); anything else is a smoke test of the path.
        "quotable": quotable,
        "not_quotable_because": None if quotable else (
            f"n={n} < {MIN_HOLDOUT_CASES}" if n < MIN_HOLDOUT_CASES
            else "the judge is not calibrated (evals/calibrate.py)"),
    }
    (args.out / f"compare-{slug(args.after)}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n")

    def show(entry: dict[str, Any]) -> str:
        value = entry["score"]
        return "no score" if value is None else f"{value:.1%}"

    def form(entry: dict[str, Any]) -> str:
        return "" if entry.get("form") is None else f", form {entry['form']:.1%}"

    print(f"before ({args.before}): {show(before)} on {before['cases']} cases, "
          f"{before['errors']} error(s){form(before)}")
    print(f"after  ({args.after}): {show(after)} on {after['cases']} cases, "
          f"{after['errors']} error(s){form(after)}")
    if delta is None:
        print("no delta: one side produced no score", file=sys.stderr)
        return 1
    print(f"delta  {delta:+.1%}" + ("" if form_delta is None else f", form {form_delta:+.1%}"))
    if not quotable:
        print(f"not quotable: {result['not_quotable_because']} -- a smoke test of the path, "
              f"recorded as such", file=sys.stderr)
    if delta < 0:
        print("the adapter scores below the base model -- do not serve it", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


_SERVE = r'''"""A development server for the comparison: the base model and an adapter
behind an OpenAI-compatible /v1/completions, in-process, on whatever this
machine has. Not the production path -- that is vLLM with --lora-modules --
but the same wire shape, so train/compare.py and the harness run here
unchanged.

    python train/serve.py --base-model <id> [--adapter artifacts/adapters/<version>/adapter]
                          [--port 8091]

The base model is served under its own name and the adapter under its
version (the adapter directory's parent), so FINETUNED_MODEL=<version>
selects the adapter and `compare.py --before <id>` selects the base.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


def load(base_model: str, adapter: Path | None) -> tuple[Any, dict[str, Any]]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.float32)
    base.eval()
    models: dict[str, Any] = {base_model: base}
    if adapter is not None:
        from peft import PeftModel

        adapted = PeftModel.from_pretrained(
            AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.float32),
            str(adapter),
        )
        adapted.eval()
        models[Path(adapter).resolve().parent.name] = adapted
    return tokenizer, models


def generate(tokenizer: Any, model: Any, prompt: str, max_tokens: int,
             stop: list[str] | None = None) -> str:
    import torch

    ids = tokenizer(prompt, return_tensors="pt")["input_ids"]
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=max_tokens, do_sample=False,
                             pad_token_id=tokenizer.pad_token_id)
    text = tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
    for marker in stop or ():
        text = text.split(marker, 1)[0]
    return text


class Handler(BaseHTTPRequestHandler):
    tokenizer: Any = None
    models: dict[str, Any] = {}
    lock = threading.Lock()

    def _send(self, code: int, body: dict[str, Any]) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - the stdlib's name
        if self.path.rstrip("/") == "/v1/models":
            self._send(200, {"data": [{"id": name} for name in self.models]})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - the stdlib's name
        if self.path.rstrip("/") != "/v1/completions":
            self._send(404, {"error": "only /v1/completions is served here"})
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        except (ValueError, TypeError):
            self._send(400, {"error": "a JSON object with model and prompt"})
            return
        model = self.models.get(body.get("model"))
        if model is None:
            self._send(404, {"error": f"model {body.get('model')!r} is not served; "
                                      f"served: {sorted(self.models)}"})
            return
        prompt = body.get("prompt")
        if not isinstance(prompt, str):
            self._send(400, {"error": "prompt must be a string"})
            return
        stop = body.get("stop")
        if isinstance(stop, str):
            stop = [stop]
        with self.lock:  # one generation at a time on a development box
            text = generate(self.tokenizer, model, prompt,
                            int(body.get("max_tokens") or 128),
                            stop if isinstance(stop, list) else None)
        self._send(200, {"choices": [{"text": text}]})

    def log_message(self, *args: Any) -> None:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--adapter", type=Path, default=None,
                        help="an adapter directory written by train/lora.py")
    parser.add_argument("--port", type=int, default=8091)
    args = parser.parse_args(argv)
    Handler.tokenizer, Handler.models = load(args.base_model, args.adapter)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"serving {sorted(Handler.models)} on http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
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
5. **Compare**: `python train/compare.py --before <id> --after <version>`,
   with `LLM_ENDPOINT` pointed at the server from step 4 (or, on the
   machine that trained, at `python train/serve.py --base-model <id>
   --adapter artifacts/adapters/<version>/adapter`, which serves both under
   the same wire shape). Refuses a holdout whose digest changed, exits
   non-zero when either side errored or the adapter scores below the base.
6. **Ship**: set `FINETUNED_MODEL=<version>` in `/etc/app/env` and restart.

## What the numbers mean

`compare.py` reports the judge's score and, where the verified answers
share an opening, a form score: the share of answers that open the same
way. A fine-tune teaches form; a judge grades content; neither number
stands in for the other. A delta is quotable only on thirty or more
holdout cases under a judge that passed `evals/calibrate.py`; below that
the record says `quotable: false` and why. Evidence is attached with the
pipeline's default `k`; a caller that sets its own `k` is served a prompt
shape the adapter did not train on.

## What the split does

`prepare.py` drops exact duplicate inputs (one case counted twice is a case
the holdout can leak), sets unverified pairs aside (they are an asset for a
verification queue, never a training set), stratifies by label so a rare
label is represented on both sides, and draws the holdout by seeded content
hash so two runs agree. The manifest records the seed, the counts per
stratum, and the digest of every file. It also lists holdout ids that also
sit in `evals/golden.jsonl`: the adapter's before/after is measured on the
holdout, and the shipped exam asks a different question.

## What the recipe does

AdamW on the adapter weights only, a linear warm-up over the first tenth
of the optimizer steps and a cosine decay to a tenth of the peak rate
over the rest, gradients clipped at norm 1.0, padded batches with the
padding masked out of attention and loss, the prompt masked out of the
loss so only the completion is learned, a seeded shuffle every epoch, the
holdout loss measured after every epoch, and the best epoch's adapter
kept -- training stops the first time the holdout loss does not fall.
`--dry-run` prints the plan, including the optimizer-step count; below
fifty steps it says so, because that is a smoke test, not a fine-tune.

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
import os
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


SERVES_WITH_EVIDENCE = "SERVES_WITH_EVIDENCE = True" in (ROOT / "train" / "lora.py").read_text()


def run(*args: str, env: dict | None = None):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


def corpus(tmp_path: Path) -> dict:
    """A two-document corpus, so --retrieve has evidence to attach."""
    root = tmp_path / "corpus"
    root.mkdir(exist_ok=True)
    (root / "fees.txt").write_text("A fee on the account statement is final once posted; "
                                   "a complaint about a fee goes to the dispute form.")
    (root / "forms.txt").write_text("The dispute form for a complaint is on the help page.")
    return {"CORPUS_DIR": str(root)}


def prepare(tmp_path: Path, out: str = "data", pairs: Path | None = None):
    extra = ["--retrieve"] if SERVES_WITH_EVIDENCE else []
    result = run("train/prepare.py", str(pairs or pairs_file(tmp_path)), "--out",
                 str(tmp_path / out), "--min-verified", "1", *extra,
                 env=corpus(tmp_path) if SERVES_WITH_EVIDENCE else None)
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


def test_the_adapter_trains_on_the_shape_it_is_served_in(tmp_path):
    """Where retrieval sits in front of reasoning the prompt carries
    evidence blocks; pairs without them are refused by the recipe, and
    --retrieve attaches the deliverable's own retriever's hits."""
    manifest = prepare(tmp_path)
    if SERVES_WITH_EVIDENCE:
        assert manifest["evidence"]["source"] == "retrieved"
        assert manifest["evidence"]["corpus_documents"] == 2
        rows = [json.loads(line) for line in
                (tmp_path / "data" / "train.jsonl").read_text().splitlines() if line.strip()]
        assert all("evidence" in row for row in rows)
        assert any(row["evidence"] for row in rows), "no evidence attached to any pair"
        bare = run("train/prepare.py", str(pairs_file(tmp_path)), "--out",
                   str(tmp_path / "bare"), "--min-verified", "1")
        assert bare.returncode == 0, bare.stderr
        result = run("train/lora.py", "--dry-run", "--base-model", "base/model",
                     "--data", str(tmp_path / "bare"))
        assert result.returncode != 0
        assert "carry none" in result.stderr
    else:
        assert manifest["evidence"]["source"] == "none"


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


def freeform_pairs(tmp_path: Path, n: int = 12) -> Path:
    rows = [{"id": f"f{i}", "input": f"How do I reset device {i}?",
             "output": f"Hold the button on device {i} for ten seconds.", "verified": True}
            for i in range(n)]
    path = tmp_path / "freeform.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_freeform_answers_are_one_stratum_with_a_holdout(tmp_path):
    """Six hundred distinct answers are not six hundred labels: stratifying
    by them once held nothing out and the recipe trained unmeasured."""
    manifest = prepare(tmp_path, "ff", pairs=freeform_pairs(tmp_path))
    assert list(manifest["strata"]) == ["all"]
    assert manifest["holdout"]["cases"] >= 2


def test_the_recipe_refuses_an_empty_holdout(tmp_path):
    rows = [{"id": "only", "input": "Q?", "output": "A.", "verified": True}]
    path = tmp_path / "one.jsonl"
    path.write_text(json.dumps(rows[0]) + "\n")
    prepare(tmp_path, "one", pairs=path)
    result = run("train/lora.py", "--dry-run", "--base-model", "base/model",
                 "--data", str(tmp_path / "one"))
    assert result.returncode != 0
    assert "holdout is empty" in result.stderr


def test_the_comparison_refuses_a_holdout_that_changed(tmp_path):
    prepare(tmp_path)
    with (tmp_path / "data" / "holdout.jsonl").open("a") as handle:
        handle.write(json.dumps({"id": "late", "input": "x", "output": "refund"}) + "\n")
    result = run("train/compare.py", "--before", "base", "--after", "adapter",
                 "--data", str(tmp_path / "data"), "--out", str(tmp_path))
    assert result.returncode == 2
    assert "not the holdout prepare.py drew" in result.stderr


def test_the_floor_in_force_is_on_the_record(tmp_path):
    """A split accepted below the recipe's floor is a smoke test, and the
    artefacts must say so; one once ran at 10 against a floor of 500 and
    nothing on disk could tell."""
    manifest = prepare(tmp_path)
    assert manifest["min_verified"] == 1 and manifest["floor_overridden"] is True
    result = run("train/lora.py", "--dry-run", "--base-model", "base/model",
                 "--data", str(tmp_path / "data"))
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["floor_overridden"] is True and plan["min_verified"] == 1
    assert "smoke test of the path" in result.stderr


def test_the_comparison_measures_nothing_when_no_model_answers(tmp_path):
    """Both sides erroring on every case once produced delta +0.0% and a
    green exit; the comparison must say it measured nothing."""
    prepare(tmp_path)
    result = run("train/compare.py", "--before", "base", "--after", "adapter",
                 "--data", str(tmp_path / "data"), "--out", str(tmp_path),
                 env={"LLM_ENDPOINT": "", "JUDGE_ENDPOINT": "", "ANTHROPIC_API_KEY": ""})
    assert result.returncode == 2, result.stdout + result.stderr
    assert "measured nothing" in result.stderr
'''
