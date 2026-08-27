---
id: churn-scoring
profile:
  output_shape: classification
  corpus_size: 2000000
  labelled_count: 50000
  interpretability_required: true
  latency_budget_ms: 10
  data_residency: cannot_leave
  hosting: customer-vpc
  human_waiting: "yes"
decisions:
  representation: classical-ml
  evaluation: labelled-metrics
  serving: self-hosted
  accountability: explainability-record
  governance: boundary-and-audit
  observability: structured-logs
  deployment: systemd-unit
  provisioning: manual-runbook
outcome: >-
  The shape holds in public production reports: gradient-boosted
  classification beating LLM approaches on cost and accuracy for narrow
  tabular tasks (Arelion/DeLaval: 97% accuracy, 80% manual-workload
  reduction, publicly reported; Airtrain: 47% to 94% accuracy with 94%
  cost reduction after moving to fine-tuned small/classical models,
  publicly reported).
sanitization: reviewed
---
An engagement shape assembled from publicly documented production
case studies. No client of ours is identifiable from it, and none
contributed to it.

Tabular classification with an interpretability obligation and a
millisecond budget. Assembled from publicly documented deployments where
classical machine learning beat generative approaches in-domain --
Arelion/DeLaval's XGBoost classification and Airtrain's published
accuracy/cost results. The shape that keeps classical ML a first-class
citizen. No private engagement contributed to this record.

The decisions above are what the engine derives from this profile
today -- reproducible by running it. The published figures cited in
the outcome belong to the public record and carry their own dates;
measured outcomes for engagements run through this framework enter
only via `fde retro`.
