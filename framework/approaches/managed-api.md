---
id: managed-api
name: Managed API
complexity: 0
components: [serving]
applies_when: [data_residency == may_leave]
avoid_when:
  - data_residency == cannot_leave
  - hosting == air-gapped
  - hosting == on-prem
  - human_waiting == no and corpus_size > 100000
  - latency_budget_ms < 100
evidence: {case_ids: [studio-style], confidence: high, last_verified: 2026-08-21}
---
Somebody else's endpoint, paid per token.

A p95 budget under a hundred milliseconds cannot be met across somebody
else's network: the round trip and their queue are spent before any work
happens. That is a physics objection, not a pricing one, which is why it is
a rule here rather than a note in the costing.

The cheapest way to be wrong cheaply: no infrastructure, no cold start, nothing
to operate. Sustained high-volume interactive traffic is where it stays cheapest
too, because self-hosting the same load means paying for redundancy and peak
headroom around the clock.

It stops being the cheapest option on high-volume work with nobody waiting:
per-token pricing at that scale runs several times what rented GPUs cost for
the same job, and the cold start nobody is waiting through costs nothing.

Sending data here is one-way. You cannot un-send it, which is a different
category of decision from an expensive one.
