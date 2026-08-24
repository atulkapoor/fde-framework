---
id: cascade
name: Cascade
complexity: 2
components: [representation, retrieval, reasoning]
applies_when: [confidence_calibrated == true and cheap_path_coverage < 0.95]
avoid_when: [confidence_calibrated == false, interpretability_required == true]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-24}
---
Do the cheap confident work; escalate the rest.

Four unrelated lines of practice describe this same shape. Entity resolution
runs deterministic rules on records carrying an exact identifier and something
probabilistic on the remainder. Model cascades try the cheapest model and
escalate only what fails a threshold, reported at roughly half to four-fifths
off while holding most of the quality. Active learning scores without labels and
sends the least confident to a human. Tiered memory keeps cheaply and promotes
deliberately.

They are one pattern, and the payoff compounds: **the records the cheap tier
could not settle are simultaneously the escalation path and the queue worth a
human's attention** -- and once verified, the additions to the golden set. One
residue, three uses.

What separates a cascade from a router is that **the decision is made on the
output, not the input**. The cheap tier attempts the work and is then judged.

Which makes calibration the whole thing rather than a detail. Confidence scores
are typically miscalibrated, and a threshold tuned on one workload routinely
fails on the next, so a cascade without a measured error rate is a cost saving
with an unknown liability attached. Ruled out where a decision must be
explained: "the cheap path was confident" is not a reason anyone accepts.
