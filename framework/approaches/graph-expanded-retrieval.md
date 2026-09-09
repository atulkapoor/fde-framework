---
id: graph-expanded-retrieval
name: Graph-expanded retrieval
complexity: 3
components: [retrieval]
applies_when: [query_pattern == multi_hop and corpus_churn == continuous]
avoid_when: [query_pattern == lookup]
evidence: {case_ids: [structured-extraction], confidence: low, last_verified: 2026-09-09}
---
Vector search finds the entry points, the entities they mention open the
graph, a bounded expansion collects what connects, and a reranker orders the
merged pool. Most of what a full graph buys on multi-hop questions -- without
asking the graph to carry recall.

That one reassignment is what survives churn. With vector search carrying
recall, the graph keeps a lighter contract -- entities and first-class edges,
rebuilt incrementally -- instead of the exhaustive index whose super-linear
growth and drifting entity resolution turn a moving corpus's graph
confidently wrong.

Where the corpus holds still, the full graph still wins: richer edges, deeper
traversal, no rerank pass to pay for. This exists for the corpus that will
not hold still. And like the reranker, it is adopted on measurement rather
than fashion: run the golden multi-hop queries and let the recall gap argue.
