---
id: ansible-playbook
component: provisioning
approach: ansible-playbook
realizations:
  - {stack: plain-python, template: provisioning/ansible-playbook.plain.py.j2, provides: Guard}
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-25}
---
Emits the provisioning artefacts for ansible-playbook.
