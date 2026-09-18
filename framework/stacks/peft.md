---
id: peft
name: PEFT (LoRA adapters)
licence: Apache-2.0
topologies: [customer-vpc, hybrid, on-prem, air-gapped, public-saas]
last_verified: 2026-09-18
reversibility: moderate
---
Parameter-efficient fine-tuning: a small adapter trained beside a frozen
base model, saved as its own directory and served next to the base weights
(vLLM `--lora-modules`) or merged into them for a server that cannot load
adapters.

Moderate reversibility rather than cheap, and the reason is not the code.
The adapter is a few hundred megabytes and rollback is pointing
`FINETUNED_MODEL` at the previous version; what is hard to reverse is
what it learned -- a mistake in the training pairs is now in weights, and
the fix is a retrain and a re-comparison, never a config change. That is
why the emitted `train/` refuses data whose digest changed and names every
adapter by what went into it.

Needs a GPU where training runs; `fde scan` says whether the card fits
the base model at this method before anyone books time on it.
