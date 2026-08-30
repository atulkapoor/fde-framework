---
id: query_pattern
type: enum
scope: functional
kind: requirement
weight: 2.0
asks: "What shape are the questions people ask?"
ask_role: [user, eval_owner, sponsor]
values: [lookup, multi_hop, comparative]
recognises:
  lookup: [find the, look up, what is the value of, retrieve the]
  multi_hop: [how are these connected, trace the relationship, across systems, chain of, connecting evidence, evidence across, connect information across, spans several documents, correlate]
  comparative: [compare, which of these, rank against, summarise across]
---
Decides how much retrieval machinery is worth building.

Published benchmarks put graph-augmented retrieval slightly *behind* plain
chunks on single-fact lookup and roughly ten points ahead on multi-hop
reasoning. So the graph is a specialised instrument rather than an upgrade: it
earns its construction cost, its two-to-three times latency and its
super-linear index growth only when a measurable share of real questions ask
how things connect rather than which text resembles a query.

Measure the share against real traffic. Assuming it is high is how a team pays
for a graph that answers questions nobody asks.
