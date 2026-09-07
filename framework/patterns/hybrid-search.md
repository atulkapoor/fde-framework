---
id: hybrid-search
component: retrieval
approach: hybrid-search
realizations:
  - {stack: plain-python, template: retrieval/hybrid-search.plain.py.j2, provides: Retriever}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-09-07}
---
Implements hybrid-search for retrieval, satisfying Retriever.
