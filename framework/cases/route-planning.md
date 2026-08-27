---
id: route-planning
profile:
  output_shape: decision
  latency_budget_ms: 200
  external_systems: 4
  existing_cluster: true
  container_competence: true
  data_residency: may_leave
  hosting: customer-vpc
  human_waiting: "yes"
decisions:
  planning: optimisation
  reasoning: optimisation
  evaluation: labelled-metrics
  integration: governed-tools
  governance: audit-only
  observability: traced
  deployment: kubernetes-manifests
  provisioning: gitops
outcome: >-
  Delivered as decided. Constraint solving produced auditable decisions a
  generative model could not guarantee; the existing cluster made
  manifests the cheap rung, and every dispatch action passed a governed
  tool boundary with an idempotency key.
sanitization: reviewed
---
A re-expressed engagement shape. No client is identifiable from it.

Constrained dispatch decisions against live operational systems, on an
existing cluster. Optimisation makes decisions; machine learning makes
predictions -- this shape is why the solver rung exists and why mutative
integrations get gates and keys.

The decisions above are what the engine derives from this profile
today -- the shape is the evidence, and it is reproducible. Measured
outcomes (days, deltas against baseline) enter only from real
retrospectives via `fde retro`; none are invented here.
