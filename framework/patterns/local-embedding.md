---
id: local-embedding
component: embedding
approach: local-embedding
realizations:
  - {stack: plain-python, template: embedding/local-embedding.plain.py.j2, provides: Mapper}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-25}
---
Implements local-embedding for the embedding component.
