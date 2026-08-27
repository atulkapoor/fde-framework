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
  Delivered as decided. Gradient-boosted trees on tabular features met the
  single-digit-millisecond budget a language model cannot, and every score
  carries its feature attribution -- which is what the interpretability
  requirement actually meant.
sanitization: reviewed
---
A re-expressed engagement shape. No client is identifiable from it.

Tabular churn prediction with an interpretability obligation and a
latency budget measured in single-digit milliseconds. The shape that keeps
classical machine learning a first-class citizen: no part of it wants a
language model, and the framework has to be able to say so.

The decisions above are what the engine derives from this profile
today -- the shape is the evidence, and it is reproducible. Measured
outcomes (days, deltas against baseline) enter only from real
retrospectives via `fde retro`; none are invented here.
