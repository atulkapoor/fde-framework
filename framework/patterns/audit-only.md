---
id: audit-only
component: governance
approach: audit-only
realizations:
  - {stack: plain-python, template: governance/audit-only.plain.py.j2, provides: Guard}
evidence: {case_ids: [churn-scoring], confidence: high, last_verified: 2026-08-25}
---
An append-only record of what happened, without enforcing where it happened.
