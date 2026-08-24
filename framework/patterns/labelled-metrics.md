---
id: labelled-metrics
component: evaluation
approach: labelled-metrics
realizations:
  - {stack: plain-python, template: evaluation/labelled-metrics.plain.py.j2, provides: Scorer}
  - {stack: xgboost, template: evaluation/labelled-metrics.xgboost.py.j2, provides: Scorer}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements labelled-metrics for evaluation, satisfying Scorer.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
