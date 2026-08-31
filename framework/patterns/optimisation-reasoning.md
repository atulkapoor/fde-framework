---
id: optimisation-reasoning
component: reasoning
approach: optimisation-reasoning
realizations:
  - {stack: plain-python, template: reasoning/optimisation.plain.py.j2, provides: Generator}
  - {stack: ortools, template: reasoning/optimisation.ortools.py.j2, provides: Generator}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements optimisation for reasoning, satisfying Generator.

The same approach serves more than one component and needs an
implementation for each: adapting weights to map fields is not the
same code as adapting them to generate text, even though the decision
that selected them is.
