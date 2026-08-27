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
  The shape holds in public production reports: batch generation against
  managed endpoints where nobody waits on a single answer, with batch
  processing and prompt engineering cutting cost per unit dramatically
  (Etsy's buyer-profile generation: 94% cost reduction per million
  users, publicly reported), and judge-based evaluation calibrated
  before scores are trusted (DoorDash's guardrail-plus-judge design,
  publicly reported).
sanitization: reviewed
---
An engagement shape assembled from publicly documented production
case studies. No client of ours is identifiable from it, and none
contributed to it.

Open-ended generation in batch, where nobody waits on any single
answer. Assembled from publicly documented deployments -- Etsy's batch
profile generation economics and DoorDash's published judge-based
evaluation design. The shape that exercises the generative path honestly:
prompted model first, calibrated judge, per-token economics over a held
fleet. No private engagement contributed to this record.

The decisions above are what the engine derives from this profile
today -- reproducible by running it. The published figures cited in
the outcome belong to the public record and carry their own dates;
measured outcomes for engagements run through this framework enter
only via `fde retro`.
