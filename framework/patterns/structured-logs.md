---
id: structured-logs
component: observability
approach: structured-logs
realizations:
  - {stack: plain-python, template: observability/structured-logs.plain.py.j2, provides: Tracer}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements structured-logs for observability, satisfying Tracer.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
