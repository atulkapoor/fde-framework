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

Prompt injection is defeated by structure, not phrasing. A user query is
data, and a retrieved document can carry instructions -- so nothing the
model reads may grant it more than the caller already has. The layers,
cheapest first: keep secrets out of the index (what was never indexed
cannot be exfiltrated -- scrub sensitive fields before representation,
not after retrieval); scope retrieval by the caller's entitlements, the
same intersection rule as tools; and screen output for the sensitive
patterns the contract names, as a fail-closed critic. "Ignore your
instructions" beats a system prompt; it does not beat an index that
never held the secret. The adversarial evals carry exfiltration probes,
and the correct answer to one is a refusal.
