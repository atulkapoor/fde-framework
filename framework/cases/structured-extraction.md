---
id: structured-extraction
profile:
  output_shape: structured
  input_format: scanned_documents
  corpus_size: 500000
  labelled_count: 10000
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
  The shape holds in public production reports: structured metadata
  extraction at hundreds of thousands of documents per week with
  ~99% field accuracy and order-of-magnitude manual-effort reduction
  (AArete's Doxy AI, publicly reported), and document processing under
  compliance boundaries on self-managed infrastructure (Deutsche Bank,
  Anthem Blue Cross, publicly reported).
sanitization: reviewed
---
An engagement shape assembled from publicly documented production
case studies. No client of ours is identifiable from it, and none
contributed to it.

High-volume field extraction from scanned documents inside a boundary
nothing may leave. Assembled from publicly documented production
deployments -- AArete's structured-extraction platform (500k documents a
week, 99% accuracy, 97% manual-effort reduction, as published), and the
compliance-bounded on-premise document systems reported by Deutsche Bank
and Anthem Blue Cross. No private engagement contributed to this record.

The decisions above are what the engine derives from this profile
today -- reproducible by running it. The published figures cited in
the outcome belong to the public record and carry their own dates;
measured outcomes for engagements run through this framework enter
only via `fde retro`.
