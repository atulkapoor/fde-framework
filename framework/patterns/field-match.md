---
id: field-match
component: evaluation
approach: field-match
realizations:
  - {stack: plain-python, template: evaluation/field-match.plain.py.j2, provides: Scorer}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements field-match for evaluation, satisfying Scorer.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
