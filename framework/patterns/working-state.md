---
id: working-state
component: memory
approach: working-state
realizations:
  - {stack: plain-python, template: memory/working-state.plain.py.j2, provides: Store}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements working-state for memory, satisfying Store.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
