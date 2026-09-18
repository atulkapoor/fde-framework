---
id: finetune
component: reasoning
approach: finetune
realizations:
  - {stack: plain-python, template: reasoning/finetune.plain.py.j2, provides: Generator}
  - {stack: peft, template: reasoning/finetune.plain.py.j2, provides: Generator}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements finetune for reasoning, satisfying Generator.

The serving side is the same under either stack: the component answers
through the adapter named by `FINETUNED_MODEL` and refuses when none is
served. The training side ships beside it as `train/` -- the seeded,
stratified, recorded split; the LoRA recipe on `peft`; the before/after
comparison on the holdout the split held back. The `peft` realization is
chosen when the client already runs it; the recipe names it either way.
