---
id: systemd-unit
component: deployment
approach: systemd-unit
realizations:
  - {stack: plain-python, template: deployment/systemd-unit.plain.py.j2, provides: Guard}
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
Emits the deployment artefacts for systemd-unit.
