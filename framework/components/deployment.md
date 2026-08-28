---
id: deployment
name: Deployment
caps: []
pipeline: false
required_when:
  - always
---
How the thing actually runs on a machine.

A ladder rather than a default, from a service unit through to a cluster. Every
rung is the right answer somewhere, and the failure this exists to prevent is
reaching past rung zero out of habit: the container runtime is cheap, and the
platform around it is not -- most of that cost being a team that now has to
operate something it did not before.

Earn the way rightward. More than one long-lived process earns a container;
multi-node scheduling or zero-downtime rolling deploys earn an orchestrator; and
one model on two GPUs earns neither.
