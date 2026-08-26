---
id: llm-representation
component: representation
approach: llm
realizations:
  - {stack: plain-python, template: representation/llm.plain.py.j2, provides: Mapper}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-27}
---
Implements llm for representation, satisfying Mapper.

The opening move for structured extraction before anything has been measured:
a model decoding into the declared contract, behind the same Mapper interface
the deterministic path satisfies -- so graduating from one to the other when
the coverage numbers arrive is a swap, not a redesign.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
