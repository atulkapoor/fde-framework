---
id: model-planner
component: planning
approach: model-planner
realizations:
  - {stack: plain-python, template: planning/model-planner.plain.py.j2, provides: Planner}
  - {stack: langgraph, template: planning/model-planner.langgraph.py.j2, provides: Planner}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements model-planner for planning, satisfying Planner.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
