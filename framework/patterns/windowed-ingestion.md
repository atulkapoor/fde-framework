---
id: windowed-ingestion
component: perception
approach: windowed-ingestion
realizations:
  - {stack: plain-python, template: perception/windowed-ingestion.plain.py.j2, provides: Parser}
evidence: {case_ids: [route-planning], confidence: medium, last_verified: 2026-08-28}
---
Implements windowed-ingestion for perception, satisfying Parser.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
