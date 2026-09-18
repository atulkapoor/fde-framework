---
id: labelled-decision
component: reasoning
approach: labelled-decision
realizations:
  - {stack: plain-python, template: reasoning/labelled-decision.plain.py.j2, provides: Generator}
evidence: {case_ids: [churn-scoring], confidence: medium, last_verified: 2026-09-18}
---
Implements labelled-decision for reasoning, satisfying Generator.

The no-framework realization is a real classifier: fitted at construction
from the shipped golden set, measured against the holdout that set never
included. A model-backed realization slots in behind the same label
contract without changing the pipeline.
