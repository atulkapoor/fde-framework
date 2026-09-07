---
id: reranked-retrieval
name: Reranked retrieval
complexity: 2
components: [retrieval]
applies_when: [query_pattern == lookup and corpus_size > 200000 and human_waiting == "no"]
avoid_when: [latency_budget_ms < 500, query_pattern == multi_hop]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-09-07}
---
A cheap retriever casts wide, a cross-encoder reads the top candidates
properly, and precision comes from the second pass. The first-stage
retriever's job quietly changes from "rank correctly" to "do not miss" --
recall at fifty, not precision at five -- which is a much easier contract to
keep on a big corpus.

The cost is a model call per query on the reranking pass, which is why the
latency budget avoids it where somebody is waiting on a tight budget: a
cross-encoder over fifty candidates is real milliseconds, and no fusion
trick refunds them.

Like the finetune rule, this is mostly reached by measurement rather than by
default: run the golden queries, look at where the right answer ranked, and
adopt the reranker when the gap between position one and position twenty is
where your answers actually live.
