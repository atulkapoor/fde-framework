---
id: retrieval
name: Retrieval
caps: [reasoning]
required_when: ["answers must be grounded in a corpus the model was not trained on"]
---
Finding the right context. Dense, sparse, hybrid, graph traversal, reranking.

Reranking is the cheapest quality improvement available in most pipelines and
the one most often skipped. Graph traversal is not a general upgrade -- it
loses to plain chunks on single-fact lookup and wins on multi-hop.
