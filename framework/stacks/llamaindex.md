---
id: llamaindex
name: LlamaIndex
licence: MIT
topologies: [public-saas, managed-api, customer-vpc, hybrid, on-prem]
last_verified: 2026-09-07
provides: {Retriever: stable}
reversibility: moderate
---
The data layer of the LLM framework stack: ingestion, indexing, query
engines, RAG plumbing. Earns its place where the client already runs it or
where the retrieval surface is complex enough (many sources, many readers)
that its connectors beat hand-rolled ingestion -- the published clinical-QA
deployments are built exactly this way.

Moderate reversibility on purpose: its index formats and query-engine
abstractions weave into the retrieval path, and unwinding them is a
re-embedding project, not a refactor. Where nothing justifies carrying the
framework, the plain-python and pgvector realizations answer the same
contract with less to own.
