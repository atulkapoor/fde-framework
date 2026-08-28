---
id: hosting
type: enum
scope: environment
kind: requirement
weight: 2.0
asks: "Where does this run?"
values: [public-saas, managed-api, customer-vpc, hybrid, on-prem, air-gapped]
# Consistent with prunes below: air-gapped and on-prem rule out may_leave.
# Hybrid is a boundary by definition -- its entire point is that the
# sensitive part stays inside while the rest may burst out, which is
# exactly what the boundary machinery pins and polices.
boundary_when: [air-gapped, on-prem, hybrid]
recognises:
  air-gapped: [air-gapped, air gapped, airgapped, no network egress]
  on-prem: [on-premise, on premises, on-prem, in our datacenter, in our data centre]
  customer-vpc: [in our vpc, our own vpc, inside our cloud account]
  managed-api: [hosted api, managed api, vendor api]
  hybrid: [hybrid, split between on-prem and cloud, burst to cloud, sensitive stays on-prem, on-prem with cloud burst]
  public-saas: [public saas, off the shelf saas]
refines:
  hybrid: on-prem
ask_role: ['admin']
prunes:
  air-gapped:
    data_residency: [may_leave]
  on-prem:
    data_residency: [may_leave]
---
An air gap is a statement about residency as much as about placement: nothing
can leave a network with no egress, so saying one settles the other and nobody
should be asked twice.

Where the compute sits. Three topologies, one architecture -- the shape does not
change between them, only placement does.

Hybrid refines on-prem for the prose reader's purposes: "sensitive stays
on-prem, burst to cloud" says both words in one sentence, and it is one
answer, not two -- the sensitive side of a hybrid *is* an on-prem.

Hybrid is the split, named: sensitive processing inside an environment the
client controls, elastic or commodity work outside it, and the boundary
between them enforced in code rather than reviewed in a document. It is the
publicly documented pattern for regulator-bound deployments that still want
cloud economics -- and the topology the boundary machinery was built for.
