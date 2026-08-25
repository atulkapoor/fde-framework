---
id: managed-embedding
name: Managed embeddings
complexity: 0
components: [embedding]
applies_when: [data_residency == may_leave]
avoid_when:
  - data_residency == cannot_leave
  - hosting == air-gapped
  - hosting == on-prem
evidence: {case_ids: [studio-style], confidence: high, last_verified: 2026-08-25}
---
A vendor endpoint. Nothing to host, nothing to keep warm, and generally better
quality per unit of effort than anything self-hosted at small scale.

Ruled out wherever the text may not leave, and for the reason people find
surprising: sending an embedding is sending the text. Vectors are recoverable
to their source, so this is not a way of anonymising anything on the way out.

One-way, like any vendor call. And expensive to reverse for a second reason --
changing embedding model means reindexing everything, so leaving is a
reindexing project rather than a configuration change.
