---
id: embeddings
type: enum
kind: requirement
asks: "Where are embeddings computed?"
values: [managed, local]
---
The least reversible decision in most retrieval systems: changing the embedding
model means reindexing the whole corpus. Decide it late, with evidence.

An embedding is not anonymised data. Sending one to a managed service is
sending the source, so a corpus under a residency constraint constrains this
too -- which is why it is pruned rather than chosen freely.
