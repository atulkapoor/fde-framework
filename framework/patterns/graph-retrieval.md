---
id: graph-retrieval
component: retrieval
approach: graph-retrieval
realizations:
  - {stack: plain-python, template: retrieval/graph-retrieval.plain.py.j2, provides: Retriever}
  - {stack: pgvector, template: retrieval/graph-retrieval.pgvector.py.j2, provides: Retriever}
  - {stack: qdrant, template: retrieval/graph-retrieval.qdrant.py.j2, provides: Retriever}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements graph-retrieval for retrieval, satisfying Retriever.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
