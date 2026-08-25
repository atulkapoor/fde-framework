---
id: audit-only
name: Audit trail
complexity: 0
components: [governance]
applies_when: [data_residency == may_leave]
avoid_when: [data_residency == cannot_leave, hosting == air-gapped]
evidence: {case_ids: [churn-scoring], confidence: high, last_verified: 2026-08-25}
---
A record of what happened, without a boundary around where it happened.

The right answer where nothing forbids egress but actions are still taken on
someone's behalf. Enforcing placement costs real complexity -- split
deployments, pinned components, a build that fails on a topology change -- and
paying for it when nothing requires it is the over-engineering the residency
question exists to prevent.

Residency and isolation are not the same requirement, and conflating them is a
known and expensive mistake. Data staying in a region satisfies one; only
staying inside a boundary satisfies the other.

What does not change: the record names the human as subject and the agent as
actor, and the trail never fails open into silence.
