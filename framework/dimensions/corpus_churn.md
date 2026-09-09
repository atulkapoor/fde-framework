---
id: corpus_churn
type: enum
scope: data
kind: requirement
weight: 1.0
asks: "How often does the document corpus itself change?"
ask_role: [admin, user]
values: [static, periodic, continuous]
recognises:
  static: [historical archive, frozen corpus, fixed set of documents, one-time snapshot, corpus is static, closed cases]
  periodic: [refreshed monthly, monthly refresh, refreshed weekly, quarterly refresh, batch refresh, re-indexed every]
  continuous: [updated continuously, constantly changing, changes daily, keeps changing, new documents arrive daily, updated throughout the day, live document feed]
---
`corpus_size` is stock and `arrival_rate` is the flow of questions; this is
how fast the stock itself turns over. Nobody volunteers it, because no demo
runs long enough to feel it.

Any index that is expensive to rebuild pays this rate forever, and the
expensive ones fail politely: retrieval keeps answering, fluently, from a
corpus that is no longer the client's. An entity graph pays the rate worst --
extraction is multi-pass, the index grows super-linearly, and entity
resolution drifts as names and structures change, which is how a graph goes
from wrong to confidently wrong without an error in any log.
