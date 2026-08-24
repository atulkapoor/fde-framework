---
id: direct-call
component: integration
approach: direct-call
realizations:
  - {stack: plain-python, template: integration/direct-call.plain.py.j2, provides: ToolBoundary}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements direct-call for integration, satisfying ToolBoundary.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
