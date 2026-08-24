---
id: representation
name: Representation
caps: [retrieval, memory, reasoning]
required_when:
  - labelled_count > 0
  - corpus_size > 0
---
How input becomes something searchable or comparable: schema mapping,
chunking, embeddings, entity resolution.

Embedding choice is the least reversible decision in most systems, because
changing it means reindexing everything. Decide it late, with evidence.
