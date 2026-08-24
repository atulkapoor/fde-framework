---
id: managed-api
component: serving
approach: managed-api
realizations:
  - {stack: plain-python, template: serving/managed-api.plain.py.j2, provides: ModelServer}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements managed-api for serving, satisfying ModelServer.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
