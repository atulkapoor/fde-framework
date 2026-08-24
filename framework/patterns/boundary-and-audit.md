---
id: boundary-and-audit
component: governance
approach: boundary-and-audit
realizations:
  - {stack: plain-python, template: governance/boundary-and-audit.plain.py.j2, provides: Guard}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements boundary-and-audit for governance, satisfying Guard.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
