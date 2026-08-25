---
id: manual-runbook
name: Written steps
complexity: 0
components: [provisioning]
applies_when: [always]
avoid_when:
  - existing_cluster == true
  - existing_iac_tool == ansible
  - existing_iac_tool == terraform
  - environment_lifetime == ephemeral
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-25}
---
Steps somebody follows, written down.

The floor, and what nothing-known resolves to. Automating a deployment before
anyone has performed it once tends to automate a guess -- and a runbook that has
been followed successfully is the only honest input to a playbook worth writing.

Not a permanent answer. It is the rung that costs least to be wrong about, and
it graduates as soon as the environment is understood well enough that repeating
the steps is tedious rather than instructive.

Ruled out where the team already runs something. Handing a written procedure to
a shop with an existing tool is asking them to do by hand what they already
automate.
