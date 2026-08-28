---
id: assisted-deterministic
name: Rules with a human queue
complexity: 1
components: [representation]
applies_when:
  - output_shape == structured and cheap_path_coverage < 0.95
  - output_shape == decision and cheap_path_coverage < 0.95
avoid_when: [confidence_calibrated == true]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-28}
---
The deterministic path for what it covers, a human queue for the rest --
and the queue is a product, not an apology.

The rung between "the rules cover nearly everything" and "bring a model":
when measured coverage is real but short, the honest system settles what
rules settle, routes the residue to people, and counts both. The queue is
simultaneously the escalation path, the verification sample, and the
golden-set additions for whatever graduates next -- one mechanism, three
jobs, which is the cascade shape with humans as the expensive tier.

Fully interpretable by construction: every settled field has a rule that
says why, every unsettled one has a person. That is why nothing here avoids
the interpretability requirement -- this is what that requirement selects.

Graduate to a model tier when the queue's cost is measured and hurts, not
before: the queue's own throughput is the number that justifies the model.

Avoided once confidence is calibrated: at that point the cascade is
the better shape -- the same cheap path, with a measured model tier
where this puts people, and people reserved for what the model cannot
settle either.
