---
id: retrieval
name: Retrieval
caps: [reasoning]
required_when:
  - output_shape == freeform
  - output_shape == ranking
---
Finding the right context. Dense, sparse, hybrid, graph traversal, reranking.

Reranking is the cheapest quality improvement available in most pipelines and
the one most often skipped. Graph traversal is not a general upgrade -- it
loses to plain chunks on single-fact lookup and wins on multi-hop.
