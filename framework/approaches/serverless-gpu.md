---
id: serverless-gpu
name: Serverless GPU
complexity: 1
components: [serving]
applies_when:
  - human_waiting == no
  - availability_target == best_effort and human_waiting != yes
avoid_when:
  - human_waiting == yes
  - data_residency == cannot_leave
  - hosting == air-gapped
  - latency_budget_ms < 100
evidence: {case_ids: [studio-style], confidence: medium, last_verified: 2026-08-21}
---
Rented GPUs that scale to zero between jobs.

A stated best-effort availability target is the same permission granted in
different words: downtime and cold starts are acceptable, so paying for a
warm fleet is paying for a promise nobody asked for.

The right answer when nobody is waiting: a multi-minute cold start is an
infrastructure detail rather than a user-experience failure, and paying nothing
between runs beats per-token pricing at volume by a wide margin.

The trap is idle time. A fleet left running overnight costs more than the work
it did, so scale-to-zero has to be real rather than nominal.
