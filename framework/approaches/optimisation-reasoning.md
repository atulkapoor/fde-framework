---
id: optimisation-reasoning
name: Constraint optimisation as the decision-maker
complexity: 1
components: [reasoning]
applies_when: [output_shape == decision]
avoid_when:
  - output_shape == freeform
  - output_shape == structured
  - output_shape == classification
  - output_shape == decision and labelled_count >= 1000
evidence: {case_ids: [route-planning], confidence: high, last_verified: 2026-08-31}
---
A solver as the reasoner, for decisions that are genuinely assignments under
constraints: crew to flights, loads to routes, stock to stores. Declared
constraints, an objective, and an answer that is optimal against what was
declared -- with the standing caveat that it is exactly as good as the
declarations.

The avoid rule is the finding from a factory-floor engagement: a per-item
decision that history has already labelled thousands of times is a
classification wearing a decision's name. Twelve thousand pass-or-repair
labels are not constraints to satisfy, they are a function to learn, and a
solver given that job has nothing to optimise. Where the labels exist, the
learned model wins; where the decision is an allocation nobody has ever
labelled, the solver does.

Split from the planning-side optimisation on purpose: an airline recovery
plan and a per-unit disposition share an algorithm family and nothing else,
and one avoid rule serving both components punished the wrong one.
