---
id: self-hosted
component: serving
approach: self-hosted
realizations:
  - {stack: plain-python, template: serving/self-hosted.plain.py.j2, provides: ModelServer}
  - {stack: vllm, template: serving/self-hosted.vllm.py.j2, provides: ModelServer}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements self-hosted for serving, satisfying ModelServer.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
