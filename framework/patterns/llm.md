---
id: llm
component: reasoning
approach: llm
realizations:
  - {stack: plain-python, template: reasoning/llm.plain.py.j2, provides: Generator}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements llm for reasoning, satisfying Generator.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
