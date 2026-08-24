---
id: text-extraction
component: perception
approach: text-extraction
realizations:
  - {stack: plain-python, template: perception/text-extraction.plain.py.j2, provides: Parser}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements text-extraction for perception, satisfying Parser.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
