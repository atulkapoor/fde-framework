---
id: manual-runbook
component: provisioning
approach: manual-runbook
realizations:
  - {stack: plain-python, template: provisioning/manual-runbook.plain.py.j2, provides: Guard}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-25}
---
Emits a runbook rather than automation.
