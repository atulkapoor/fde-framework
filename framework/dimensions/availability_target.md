---
id: availability_target
type: enum
scope: non_functional
kind: requirement
weight: 1.0
asks: "What availability does this need -- always on, business hours, or best effort?"
values: [always_on, business_hours, best_effort]
recognises:
  always_on: [always on, 24/7, around the clock, no downtime, five nines, high availability]
  business_hours: [business hours, nine to five, office hours only]
  best_effort: [best effort, downtime is fine, downtime is acceptable, can be down]
ask_role: ['sponsor', 'admin']
---
The fleet is sized for compute; this is what sizes it for absence. A single
replica behind a systemd unit is a fine answer until the sentence "it cannot
be down during a deploy" is spoken, and that sentence changes the deployment
story, the spare count, and what the runbook promises -- so it has to be
asked, not discovered during the first outage.

The emitted ops/slo.md carries this target next to the latency budget, and
best_effort is a legitimate answer that saves real money: a nightly batch
nobody waits for needs no spare.
