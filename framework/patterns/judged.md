---
id: judged
component: evaluation
approach: judged
realizations:
  - {stack: plain-python, template: evaluation/judged.plain.py.j2, provides: Scorer}
  - {stack: local-judge, template: evaluation/judged.local-judge.py.j2, provides: Scorer}
  - {stack: openai-judge, template: evaluation/judged.openai-judge.py.j2, provides: Scorer}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements judged for evaluation, satisfying Scorer.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
