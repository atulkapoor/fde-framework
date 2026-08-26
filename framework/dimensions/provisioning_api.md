---
id: provisioning_api
type: boolean
kind: environment
weight: 0.5
asks: "Is there an API that creates and destroys the infrastructure?"
ask_role: [admin]
recognises:
  "true": [cloud account, we use aws, on azure, vsphere api, openstack]
  "false": [bare metal, racked by hand, physical servers, no cloud]
---
Whether infrastructure has a lifecycle something can manage.

Where a person racked the machines there is nothing to create and nothing to
destroy, and a state file tracks zero resources. That is the case where
declarative provisioning is carrying weight for no benefit -- the machines exist,
and what remains is configuring them.
