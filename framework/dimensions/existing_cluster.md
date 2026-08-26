---
id: existing_cluster
type: boolean
kind: environment
weight: 1.0
asks: "Is there already a cluster this could run on?"
ask_role: [admin]
recognises:
  "true": [we have a cluster, our kubernetes, existing k8s, our openshift, we run rke2]
---
Whether a platform already exists to deploy onto.

Reuse-first applies to platforms more than to anything else. A cluster somebody
already operates -- already backed up, already patched, already on somebody's
pager -- is far cheaper than the same capability standing beside it, and the
tenth workload on it costs almost nothing.

The inverse is the expensive mistake: standing up a cluster for one workload
buys an upgrade treadmill and a set of failure modes for a deployment that
wanted a service unit.
