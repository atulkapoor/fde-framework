---
id: local-embedding
name: Local embeddings
complexity: 1
components: [embedding]
applies_when: [data_residency == cannot_leave, hosting == air-gapped, hosting == on-prem]
avoid_when: [operates_after_handover == nobody_yet and data_residency == may_leave]
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
An embedding model running inside the boundary.

Chosen because something forbids the alternative rather than because it is
better. Small embedding models are cheap to run and unremarkable to operate,
which makes this a far lighter obligation than self-hosting a generation model
-- but it is still a model somebody has to keep running after the engagement
ends.

Ruled out where nobody is named to operate it. A model with no owner is a
liability handed over with a bow on it, and an embedding model whose host dies
takes the index with it.

The handover concern is stated precisely rather than broadly: with nobody
named to operate and data free to leave, the managed alternative is
strictly simpler and wins. But where data cannot leave, the plain
realization is an in-process library call whose operational burden is the
application's own -- the broad version of this avoid once treated a
library import like a GPU fleet, and stranded every engagement inside a
boundary.
