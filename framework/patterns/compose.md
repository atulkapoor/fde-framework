---
id: compose
component: deployment
approach: compose
realizations:
  - {stack: plain-python, template: deployment/compose.plain.py.j2, provides: Guard}
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
Emits the deployment artefacts for compose.
