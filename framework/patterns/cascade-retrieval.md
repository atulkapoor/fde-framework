---
id: cascade-retrieval
component: retrieval
approach: cascade
realizations:
  - {stack: plain-python, template: retrieval/cascade.plain.py.j2, provides: Retriever}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-24}
---
Cheap tier first, escalation on measured low confidence, and the escalated set
returned as the verification queue.
