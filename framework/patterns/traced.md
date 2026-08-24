---
id: traced
component: observability
approach: traced
realizations:
  - {stack: plain-python, template: observability/traced.plain.py.j2, provides: Tracer}
  - {stack: opentelemetry, template: observability/traced.opentelemetry.py.j2, provides: Tracer}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements traced for observability, satisfying Tracer.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
