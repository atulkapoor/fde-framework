---
id: boundary-and-audit
name: Boundary and audit
complexity: 1
components: [governance]
applies_when: [data_residency == cannot_leave, hosting == air-gapped]
avoid_when: [access_model == role_based, data_residency == may_leave]
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Not needed where nothing forbids egress -- a boundary around data free to
move is ceremony. Placement enforced structurally, and an append-only record of what happened.

Entitlements are inherited, never granted: what an agent may do is the
intersection of what the delegating person may do, what it is scoped to, and
what the tool requires. Never a union.

The audit names the human as subject and the agent as actor. A record saying an
agent issued a refund has lost the accountability chain.
