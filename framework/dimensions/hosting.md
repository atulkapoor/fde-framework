---
id: hosting
type: enum
kind: requirement
asks: "Where does this run?"
values: [public-saas, managed-api, customer-vpc, on-prem, air-gapped]
recognises:
  air-gapped: [air-gapped, air gapped, airgapped, no network egress]
  on-prem: [on-premise, on premises, on-prem, in our datacenter, in our data centre]
  customer-vpc: [in our vpc, our own vpc, inside our cloud account]
  managed-api: [hosted api, managed api, vendor api]
  public-saas: [public saas, off the shelf saas]
prunes:
  air-gapped:
    inference: [hosted-api]
    embeddings: [managed]
  on-prem:
    inference: [hosted-api]
ask_role: ['admin']
---
Where the compute sits. Three topologies, one architecture -- the shape does not
change between them, only placement does.
