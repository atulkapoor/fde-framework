---
id: embedding
name: Embedding
caps: [retrieval, memory]
required_when:
  - query_pattern == comparative
  - query_pattern == multi_hop
---
Turning text into vectors, and deciding where that happens.

Caps retrieval and memory alike: a poor embedding sets a ceiling neither a
reranker nor a better model gets past, because the thing that was not
represented cannot be retrieved.

**The least reversible decision in a retrieval system.** Changing the model
means reindexing the entire corpus, so it is made late, with evidence, and after
the cheaper choices have been settled.

Placement is not a separate question from residency. An embedding is
recoverable to its source, so computing one through a vendor is sending the
text -- and a store holding embeddings of regulated data is in scope for the
boundary. "We only send vectors" is the version of this that sounds safe and
is not.
