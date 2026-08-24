---
id: optimisation
component: planning
approach: optimisation
realizations:
  - {stack: plain-python, template: planning/optimisation.plain.py.j2, provides: Planner}
  - {stack: ortools, template: planning/optimisation.ortools.py.j2, provides: Planner}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements optimisation for planning, satisfying Planner.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
