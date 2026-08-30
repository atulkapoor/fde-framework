---
id: deterministic-masking
component: redaction
approach: deterministic-masking
realizations:
  - {stack: plain-python, template: redaction/deterministic-masking.plain.py.j2, provides: Mapper}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-30}
---
Implements deterministic-masking for redaction, satisfying Mapper.
