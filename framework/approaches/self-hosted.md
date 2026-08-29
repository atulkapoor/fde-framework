---
id: self-hosted
name: Self-hosted
complexity: 2
components: [serving]
applies_when:
  - data_residency == cannot_leave
  - hosting == air-gapped
  - hosting == on-prem
  - hosting == hybrid
  - latency_budget_ms < 100
avoid_when:
  - operates_after_handover == nobody_yet
  - accelerator == none and human_waiting == yes
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Open weights on hardware you control.

Chosen because something forbids the alternative, not because it is cheaper --
at sustained interactive load it usually is not, once redundancy, peak headroom
and prefill overhead are counted. Naive sizing understates the fleet
substantially: a replica is however many devices the weights and cache need
together, and pricing each replica as one device quotes a large model's fleet
at a fraction of its cost.

When the hardware will not hold the model, three levers in order:
quantisation, then parameter-efficient adaptation, then distillation. Each costs
more effort and more quality risk than the one before, so stop at the first that
fits.

Serving stacks cache at four layers that share one word and nothing else: the
KV cache lives for one request, prefix caching keeps those tensors across
requests on the server, provider prompt caching is the same idea on somebody
else's hardware, and a semantic cache stores whole responses by similarity.
The first three hit only on exact token identity, which is why sticky routing
matters on a self-hosted fleet -- a request that lands on a replica holding
its prefix skips the prefill that dominates time-to-first-token -- and why a
model switch is a cache reset: entries are keyed to the model that made them.
