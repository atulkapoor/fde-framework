---
id: kubernetes-manifests
name: Cluster manifests
complexity: 2
components: [deployment]
applies_when: [existing_cluster == true, external_systems > 2]
avoid_when: [container_competence == false and existing_cluster == false]
evidence: {case_ids: [route-planning], confidence: high, last_verified: 2026-08-25}
---
Manifests applied to a cluster that already exists.

Cheap when the cluster is there and somebody else patches it -- the tenth
workload costs almost nothing, which is the entire argument for a platform.

Expensive when it is not. Standing up a cluster for one deployment buys a
control plane, an upgrade cadence and a set of failure modes for something that
wanted a service unit, and the cost lands on whoever is still there in a year.

Competence gates this only where no cluster exists yet. A cluster already running means somebody operates it -- manifests are how that shop deploys, whatever this team's container practice, and blocking the only cluster-native option on the applying team's skills would leave a cluster shop with no way to deploy at all.
