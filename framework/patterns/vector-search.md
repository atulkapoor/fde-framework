---
id: vector-search
component: retrieval
approach: vector-search
realizations:
  - {stack: plain-python, template: retrieval/vector-search.plain.py.j2, provides: Retriever}
  - {stack: pgvector, template: retrieval/vector-search.pgvector.py.j2, provides: Retriever}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements vector-search for retrieval, satisfying Retriever.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
