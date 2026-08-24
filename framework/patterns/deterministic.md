---
id: deterministic
component: representation
approach: deterministic
realizations:
  - {stack: plain-python, template: representation/deterministic.plain.py.j2, provides: Mapper}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements deterministic for representation, satisfying Mapper.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
