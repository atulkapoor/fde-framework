---
id: manual-runbook
name: Written steps
complexity: 2
components: [provisioning]
applies_when: [always]
avoid_when:
  - existing_cluster == true
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

Complexity 2, not 0, and the number is the design: complexity orders by
cost of ownership, and a runbook is recurring human labour forever --
every automated tool that applies beats it on that measure, which is the
preference expressed without a single avoid rule. When the better tools
are blocked (an Ansible shop with an ephemeral environment, a Terraform
shop with no API), nothing avoids the runbook, and the floor holds.
Ephemeral by hand is painful and is said so here; painful is not the same
as impossible.
