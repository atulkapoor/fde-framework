---
id: self-hosted
name: Self-hosted
complexity: 2
components: [serving]
applies_when: [data_residency == cannot_leave, hosting == air-gapped, hosting == on-prem]
avoid_when:
  - operates_after_handover == nobody_yet
  - accelerator == none and human_waiting == yes
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Open weights on hardware you control.

Chosen because something forbids the alternative, not because it is cheaper --
at sustained interactive load it usually is not, once redundancy, peak headroom
and prefill overhead are counted. Naive sizing understates the fleet
substantially: a replica is however many devices the weights and cache need
together, and pricing each replica as one device quotes a large model's fleet
at a fraction of its cost.

When the hardware will not hold the model, three levers in order:
quantisation, then parameter-efficient adaptation, then distillation. Each costs
more effort and more quality risk than the one before, so stop at the first that
fits.
