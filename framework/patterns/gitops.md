---
id: gitops
component: provisioning
approach: gitops
realizations:
  - {stack: plain-python, template: provisioning/gitops.plain.py.j2, provides: Guard}
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
Emits the provisioning artefacts for gitops.
