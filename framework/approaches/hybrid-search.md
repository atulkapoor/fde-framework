---
id: hybrid-search
name: Hybrid search
complexity: 2
components: [retrieval]
applies_when: [query_pattern == comparative and corpus_size > 100000]
avoid_when: [query_pattern == multi_hop, corpus_size < 10000]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-09-07}
---
Keyword and semantic retrieval fused, because each fails where the other
holds: exact identifiers, part numbers and names that embeddings blur past
are what BM25 was built for, and paraphrase is what it cannot see. Fusion
(reciprocal rank, not score mixing -- scores from different retrievers do
not share a scale) takes both.

Earns its second index where the corpus is large enough that either
retriever alone leaves recall on the table, and comparative queries mix
named things with described things. Below ten thousand documents, one good
retriever plus a rerank is less to operate than two indexes that must stay
in sync -- the sync is the real cost, and it fails silently.

Reached by override wherever the sample queries show identifier-plus-prose
mixtures the chosen retriever measurably misses; the golden set is the
evidence, never the hunch.
