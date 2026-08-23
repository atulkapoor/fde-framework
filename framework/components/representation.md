---
id: representation
name: Representation
caps: [retrieval, memory, reasoning]
required_when: ["input must be mapped onto a schema or an embedding space"]
---
How input becomes something searchable or comparable: schema mapping,
chunking, embeddings, entity resolution.

Embedding choice is the least reversible decision in most systems, because
changing it means reindexing everything. Decide it late, with evidence.
