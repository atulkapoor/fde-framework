---
id: systemd-unit
name: Service unit
complexity: 0
components: [deployment]
applies_when: [always]
avoid_when:
  - existing_cluster == true
  - external_systems > 2
  - container_competence == true
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
A virtual environment and a service unit. No container, no orchestrator, no
registry.

The floor of the ladder, so this is what nothing-known resolves to: it is the
rung that costs least if it turns out to be wrong, and every rung above it has
to be earned by something in the profile.

Rung zero, and frequently the correct answer rather than the lesser one. For a
single-node deployment serving one thing, this is understood by everyone who has
ever administered a Linux box, restarts on failure, starts on boot, and adds
nothing anybody has to learn.

Reaching past it costs a competency the team may not have and a platform
somebody has to keep patched. That cost is real and is paid every month.
