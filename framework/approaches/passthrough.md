---
id: passthrough
name: Pass through
complexity: 0
components: [perception]
applies_when: [input_format == structured_data]
avoid_when: [input_format == scanned_documents, input_format == documents, input_format == images]
evidence: {case_ids: [churn-scoring], confidence: high, last_verified: 2026-08-21}
---
Data that already has a schema needs validating, not parsing. The cheapest
perception is none.
