---
id: kubernetes-manifests
component: deployment
approach: kubernetes-manifests
realizations:
  - {stack: plain-python, template: deployment/kubernetes-manifests.plain.py.j2, provides: Guard}
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
Emits the deployment artefacts for kubernetes-manifests.
