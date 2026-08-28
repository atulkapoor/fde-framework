---
id: segmentation
component: representation
approach: segmentation
realizations:
  - {stack: plain-python, template: representation/segmentation.plain.py.j2, provides: Parser}
evidence: {case_ids: [studio-style], confidence: medium, last_verified: 2026-08-28}
---
Implements segmentation for representation, satisfying Parser.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
