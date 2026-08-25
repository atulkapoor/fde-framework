---
id: ansible-playbook
name: Convergent configuration
complexity: 1
components: [provisioning]
applies_when: [existing_iac_tool == ansible, provisioning_api == false]
avoid_when: [existing_cluster == true, environment_lifetime == ephemeral]
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
Machines brought towards a described state, over plain SSH.

The right answer on hardware somebody racked, where there is nothing to create
and everything to configure. Also the right answer wherever the team already
lives here, cloud or not -- it provisions perfectly well through cloud modules,
and the argument that it is only for configuration is taxonomy rather than
operations.

Its genuine limit: no concept of un-doing. There is no destroy, so an
environment that must vanish cleanly wants the declarative option instead.

It travels well into an air gap: SSH, no agent, and collections vendored
alongside.
