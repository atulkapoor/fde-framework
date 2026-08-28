---
id: assisted-deterministic
component: representation
approach: assisted-deterministic
realizations:
  - {stack: plain-python, template: representation/assisted.plain.py.j2, provides: Mapper}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-28}
---
Implements assisted-deterministic for representation, satisfying Mapper --
the same contract the deterministic path satisfies, so measuring one
against the other is a swap.
