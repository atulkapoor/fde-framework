---
id: graph-retrieval
name: Graph retrieval
complexity: 3
components: [retrieval]
applies_when: [query_pattern == multi_hop]
avoid_when: [query_pattern == lookup, query_pattern == comparative]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Explicit entities and edges, traversed at query time.

Worth its cost only where similarity search structurally cannot answer -- how
two things connect, rather than which text resembles a query. On single-fact
lookup it measurably loses to plain chunks, so this is a specialised instrument
rather than an upgrade.

The costs are real: multi-pass extraction to build it, two to three times the
end-to-end latency to use it, and an index that grows super-linearly, which is
what makes incremental updates painful on a corpus that changes.

Published gains also warrant scepticism -- judge position bias has been shown to
swing reported win rates by tens of points. Measure on your own traffic.
