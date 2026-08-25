---
id: provisioning
name: Provisioning
caps: []
required_when:
  - always
---
Who applies the infrastructure, and with what.

Not a taxonomy question. What decides it is whether there is an API to call at
all, whether the environment must be destroyed cleanly, and -- most of all -- what
the team already operates, because they maintain this after the engagement ends
and the thing they cannot maintain is the thing that rots.

"Neither" is a real answer. Where a cluster already exists, the infrastructure
is somebody else's problem and what remains is application manifests.
