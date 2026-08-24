---
id: serverless-gpu
component: serving
approach: serverless-gpu
realizations:
  - {stack: plain-python, template: serving/serverless-gpu.plain.py.j2, provides: ModelServer}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements serverless-gpu for serving, satisfying ModelServer.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
