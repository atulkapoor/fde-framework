---
id: optimisation
name: Optimisation
complexity: 1
components: [planning, reasoning]
applies_when: [output_shape == decision]
avoid_when: [output_shape == freeform, output_shape == structured, output_shape == classification]
evidence: {case_ids: [route-planning], confidence: high, last_verified: 2026-08-21}
---
Constraint solvers and mathematical programming.

**Optimisation makes decisions; machine learning makes predictions.** Where the
problem is to allocate, schedule, route or select subject to hard constraints, a
solver answers it exactly and proves the answer feasible. A model trained to
imitate past decisions will produce something plausible that violates a
constraint, and will not tell you it did.

The two combine well -- predict demand, then optimise against it -- but the
prediction is not the decision.
