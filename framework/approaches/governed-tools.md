---
id: governed-tools
name: Governed tool boundary
complexity: 1
components: [integration]
applies_when: [external_systems > 1]
avoid_when: [external_systems < 2]
evidence: {case_ids: [route-planning], confidence: high, last_verified: 2026-08-21}
---
One entry point through which every outward call passes, each tool declaring a
typed schema, the scope it requires, and whether it changes anything.

Past the first system this stops being tidiness: it is the only place
authentication, authorisation and audit can be enforced once instead of per
caller. The mutative flag is what lets the autonomy move find the steps needing
a gate and an idempotency key, without anyone remembering to add them.

An unregistered tool cannot be called. That is the property, not a policy.
