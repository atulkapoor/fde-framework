---
id: fixed-sequence
component: planning
approach: fixed-sequence
realizations:
  - {stack: plain-python, template: planning/fixed-sequence.plain.py.j2, provides: Planner}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements fixed-sequence for planning, satisfying Planner.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
