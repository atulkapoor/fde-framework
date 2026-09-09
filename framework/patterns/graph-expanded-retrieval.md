---
id: graph-expanded-retrieval
component: retrieval
approach: graph-expanded-retrieval
realizations:
  - {stack: plain-python, template: retrieval/graph-expanded-retrieval.plain.py.j2, provides: Retriever}
  - {stack: pgvector, template: retrieval/graph-expanded-retrieval.pgvector.py.j2, provides: Retriever}
  - {stack: qdrant, template: retrieval/graph-expanded-retrieval.qdrant.py.j2, provides: Retriever}
evidence: {case_ids: [structured-extraction], confidence: low, last_verified: 2026-09-09}
---
Implements graph-expanded-retrieval for retrieval, satisfying Retriever.

Vector entry, entity expansion, rerank exit. The graph is deliberately the
junior partner: it contributes connections, never recall, which is what lets
it stay small enough to rebuild as the corpus moves.
