---
id: gitops
name: Manifests in version control
complexity: 0
components: [provisioning]
applies_when: [existing_cluster == true]
avoid_when: [existing_cluster == false]
evidence: {case_ids: [route-planning], confidence: medium, last_verified: 2026-08-25}
---
The desired state in a repository, reconciled onto a cluster that already exists.

"Neither provisioner" as a real answer. Where the infrastructure is somebody
else's problem, adding one provisions nothing and gives an FDE a second thing to
hand over.

What it buys instead is that the deployed state is reviewable and revertable by
whoever already reviews changes, which is usually the property people wanted
from a provisioning tool in the first place.
