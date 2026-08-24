---
id: classical-ml-reasoning
component: reasoning
approach: classical-ml
realizations:
  - {stack: plain-python, template: reasoning/classical-ml.plain.py.j2, provides: Generator}
  - {stack: xgboost, template: reasoning/classical-ml.xgboost.py.j2, provides: Generator}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements classical-ml for reasoning, satisfying Generator.

The same approach serves more than one component and needs an
implementation for each: adapting weights to map fields is not the
same code as adapting them to generate text, even though the decision
that selected them is.
