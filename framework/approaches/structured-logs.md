---
id: structured-logs
name: Structured logs
complexity: 0
components: [observability]
applies_when: [always]
avoid_when: [external_systems > 1]
evidence: {case_ids: [churn-scoring], confidence: high, last_verified: 2026-08-21}
---
Machine-readable events with correlation identifiers. Enough for a pipeline
whose path you can enumerate.
