---
id: decision-log
name: Decision log
complexity: 0
components: [accountability]
applies_when: [interpretability_required == true]
avoid_when:
  - output_shape == freeform
  - output_shape == classification
  - output_shape == ranking
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
Every decision kept with its inputs and the rule that produced it.

Enough where the decision came from a rule: replaying the rule against the
recorded inputs reproduces the outcome exactly, which is the strongest form of
explanation available and needs no model to generate it.

Not enough where the decision came from a model. There, the inputs and the
outcome do not reconstruct the reasoning, and something that attributes the
outcome to its drivers is required instead.
