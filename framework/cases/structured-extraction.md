---
id: structured-extraction
profile:
  output_shape: structured
  input_format: scanned_documents
  corpus_size: 200000
  labelled_count: 8000
  data_residency: cannot_leave
  hosting: on-prem
  external_systems: 3
  human_waiting: "yes"
  operates_after_handover: platform_team
  container_competence: false
  existing_cluster: false
decisions:
  perception: ocr-pipeline
  representation: deterministic
  evaluation: field-match
  governance: boundary-and-audit
  integration: governed-tools
  observability: traced
  deployment: systemd-unit
  provisioning: manual-runbook
outcome: >-
  Delivered as decided. The deterministic mapper carried the measured
  coverage with the unmapped residue routed to a human queue; the same
  queue seeded golden-set additions. Rung-zero deployment held for a
  team with no container practice.
sanitization: reviewed
---
A re-expressed engagement shape. No client is identifiable from it.

High-volume field extraction from scanned documents, inside a
boundary nothing may leave. The flagship shape: it exercises the OCR
ladder, the deterministic-first extraction rung, offline evaluation, and
the boundary machinery end to end.

The decisions above are what the engine derives from this profile
today -- the shape is the evidence, and it is reproducible. Measured
outcomes (days, deltas against baseline) enter only from real
retrospectives via `fde retro`; none are invented here.
