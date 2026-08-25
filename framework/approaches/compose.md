---
id: compose
name: Compose
complexity: 1
components: [deployment]
applies_when: [container_competence == true]
avoid_when: [existing_cluster == true, container_competence == false]
evidence: {case_ids: [studio-style], confidence: high, last_verified: 2026-08-25}
---
Several containers on one host, declared together.

The right rung for more than one long-lived process where multi-node scheduling
is not required. Isolation and reproducible dependencies without a control
plane, an etcd or an upgrade treadmill.

Its limit is honest and worth stating up front: one host. When that host is
being restarted, the service is down, and if that is unacceptable the next rung
is the answer rather than a workaround here.
