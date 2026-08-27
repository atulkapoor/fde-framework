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
  The shape holds in decades of published operations-research practice:
  constraint solvers producing auditable dispatch decisions at fleet
  scale (the publicly documented route-optimisation programmes of large
  logistics operators), with generative models absent from the decision
  path because a solver's output is provable and a model's is not.
sanitization: reviewed
---
An engagement shape assembled from publicly documented production
case studies. No client of ours is identifiable from it, and none
contributed to it.

Constrained dispatch decisions against live operational systems.
Anchored in the public operations-research record -- large-scale fleet
route optimisation is among the most documented solver deployments in
industry -- rather than any private engagement. Optimisation makes
decisions; machine learning makes predictions; this shape is why the
solver rung exists and why mutative integrations get gates and keys.

The decisions above are what the engine derives from this profile
today -- reproducible by running it. The published figures cited in
the outcome belong to the public record and carry their own dates;
measured outcomes for engagements run through this framework enter
only via `fde retro`.
