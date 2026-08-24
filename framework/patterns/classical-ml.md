---
id: classical-ml
component: representation
approach: classical-ml
realizations:
  - {stack: plain-python, template: representation/classical-ml.plain.py.j2, provides: Mapper}
  - {stack: xgboost, template: representation/classical-ml.xgboost.py.j2, provides: Mapper}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements classical-ml for representation, satisfying Mapper.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
