---
id: episodic-store
component: memory
approach: episodic-store
realizations:
  - {stack: plain-python, template: memory/episodic-store.plain.py.j2, provides: Store}
  - {stack: pgvector, template: memory/episodic-store.pgvector.py.j2, provides: Store}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements episodic-store for memory, satisfying Store.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
