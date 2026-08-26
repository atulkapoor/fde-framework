---
id: external_systems
type: count
kind: requirement
weight: 0.5
asks: "How many systems does this have to touch?"
ask_role: [admin]
recognises_near: [systems, integrations, apis, endpoints, services]
---
One is a call. Several is a boundary.

Past the first, the argument for a single governed entry point stops being
tidiness and becomes the only place authentication, authorisation and audit can
be enforced once rather than per caller.
