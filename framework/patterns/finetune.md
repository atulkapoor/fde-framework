---
id: finetune
component: reasoning
approach: finetune
realizations:
  - {stack: plain-python, template: reasoning/finetune.plain.py.j2, provides: Generator}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements finetune for reasoning, satisfying Generator.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
