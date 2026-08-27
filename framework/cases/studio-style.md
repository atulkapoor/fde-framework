---
id: studio-style
profile:
  output_shape: freeform
  human_waiting: "no"
  data_residency: may_leave
  hosting: customer-vpc
  corpus_size: 5000
  container_competence: true
  existing_cluster: false
  environment_lifetime: ephemeral
  provisioning_api: true
decisions:
  reasoning: llm
  serving: managed-api
  evaluation: judged
  governance: audit-only
  observability: structured-logs
  deployment: compose
  provisioning: terraform-module
outcome: >-
  Delivered as decided. Batch generation with nobody waiting made a
  managed endpoint the honest economics; the judged evaluation was
  calibrated against human agreement before any score was quoted, and the
  ephemeral environment tears down cleanly because the provisioner tracks
  what it created.
sanitization: reviewed
---
A re-expressed engagement shape. No client is identifiable from it.

Open-ended stylistic generation in batch, where nobody waits on any
single answer. The shape that exercises the generative path honestly:
prompted model first, judge-based evaluation with calibration, and
economics that favour paying per token over holding a fleet.

The decisions above are what the engine derives from this profile
today -- the shape is the evidence, and it is reproducible. Measured
outcomes (days, deltas against baseline) enter only from real
retrospectives via `fde retro`; none are invented here.
