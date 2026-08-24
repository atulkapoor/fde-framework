---
id: vector-search
name: Vector search
complexity: 1
components: [retrieval]
applies_when: [query_pattern == lookup, query_pattern == comparative]
avoid_when: [query_pattern == multi_hop]
evidence: {case_ids: [studio-style], confidence: high, last_verified: 2026-08-21}
---
Similarity over embeddings, usually with a reranker in front of the results.

Reranking is the cheapest quality gain available in most pipelines and the one
most often skipped: single-digit point lifts for a couple of hundred
milliseconds, without touching the index.

The embedding model is the least reversible choice in the system, since changing
it means reindexing everything. Decide it late.
