---
id: hosting
type: enum
kind: requirement
asks: "Where does this run?"
values: [public-saas, managed-api, customer-vpc, on-prem, air-gapped]
# Consistent with prunes below: both values rule out may_leave, so both place
# the engagement inside a boundary.
boundary_when: [air-gapped, on-prem]
recognises:
  air-gapped: [air-gapped, air gapped, airgapped, no network egress]
  on-prem: [on-premise, on premises, on-prem, in our datacenter, in our data centre]
  customer-vpc: [in our vpc, our own vpc, inside our cloud account]
  managed-api: [hosted api, managed api, vendor api]
  public-saas: [public saas, off the shelf saas]
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
