---
id: terraform-module
name: Declarative provisioning
complexity: 1
components: [provisioning]
applies_when: [provisioning_api == true, environment_lifetime == ephemeral]
avoid_when:
  - provisioning_api == false
  - existing_cluster == true
  - existing_iac_tool == ansible
evidence: {case_ids: [studio-style], confidence: high, last_verified: 2026-08-25}
---
Resources declared, with state tracked so they can be destroyed again.

The one capability a convergence tool does not have: it knows what it created,
so it can show drift and take it all away. That matters for environments that
must vanish -- per-branch, per-pilot, per-demo -- and is bookkeeping for a cluster
that lives five years.

Ruled out where the team runs something else, because the tool they cannot
maintain is the one that rots. And ruled out on bare metal, where there is no
API to call and the state file would track nothing.
