---
id: finetune-representation
component: representation
approach: finetune
realizations:
  - {stack: plain-python, template: representation/finetune.plain.py.j2, provides: Mapper}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements finetune for representation, satisfying Mapper.

The same approach serves more than one component and needs an
implementation for each: adapting weights to map fields is not the
same code as adapting them to generate text, even though the decision
that selected them is.
