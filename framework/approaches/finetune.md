---
id: finetune
name: Fine-tuning
complexity: 3
components: [reasoning, representation]
applies_when: [output_shape == freeform and labelled_count >= 1000]
avoid_when: [output_shape == classification, output_shape == decision]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Adapting a model's behaviour: tone, house style, output shape, schema mapping.

**For behaviour, never for facts.** Fine-tuning teaches a model *how* to
respond, not *what* is true; anything that changes weekly belongs in retrieval,
not in weights. Train only on verified pairs -- unverified rows are an asset,
but they are mined rather than trained on.

The label count is in the applies condition because it is the whole question:
adaptation without enough verified pairs is not available, whatever the output
shape, and an approach that never asked how many labels exist would recommend
training on hope.

Expensive to reverse: a change means retraining and re-evaluating. Earn it.
