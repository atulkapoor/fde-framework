---
id: governance
name: Governance
caps: []
required_when:
  - data_residency == cannot_leave
  - data_residency == may_leave
  - hosting == air-gapped
---
Identity, delegated authority, guardrails, approval gates, audit and ledger.

**Guardrails run alongside every step, never only at the entry point.** A gate
on the input does nothing about what the system decides to do on step four,
which is where the damage happens.

Entitlements are inherited, never granted: what an agent may do is the
intersection of what the delegating human may do, what the agent is scoped to,
and what the tool requires. Never a union.
