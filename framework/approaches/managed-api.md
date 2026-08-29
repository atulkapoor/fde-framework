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
  - human_waiting == no and arrival_rate > 50000
  - latency_budget_ms < 100
evidence: {case_ids: [studio-style], confidence: high, last_verified: 2026-08-21}
---
Somebody else's endpoint, paid per token.

A p95 budget under a hundred milliseconds cannot be met across somebody
else's network: the round trip and their queue are spent before any work
happens. That is a physics objection, not a pricing one, which is why it is
a rule here rather than a note in the costing.

The volume objection is really about flow, not stock: fifty thousand
requests a day with nobody waiting is sustained work that rented GPUs do
for a fraction of per-token pricing, whatever the archive size says.

The cheapest way to be wrong cheaply: no infrastructure, no cold start, nothing
to operate. Sustained high-volume interactive traffic is where it stays cheapest
too, because self-hosting the same load means paying for redundancy and peak
headroom around the clock.

It stops being the cheapest option on high-volume work with nobody waiting:
per-token pricing at that scale runs several times what rented GPUs cost for
the same job, and the cold start nobody is waiting through costs nothing.

Sending data here is one-way. You cannot un-send it, which is a different
category of decision from an expensive one.

Provider prompt caching changes the arithmetic before any sizing does: reused
prompt prefixes bill at a fraction of the input rate, but only on exact token
match. That makes prompt hygiene a production concern, not an optimisation --
variable content (timestamps, user names) placed early in the prompt
invalidates every cached block after it, and rewriting history (summarising)
re-bills the whole prefix where trimming it in place stays byte-identical. A
semantic cache is a different animal: it returns stored responses on
similarity, skips the model entirely, and can return a confidently wrong
answer with a success status -- a sentence and its negation embed close
together. It is a retrieval system wearing a cache's name, and it needs the
same evaluation any retrieval gets.
