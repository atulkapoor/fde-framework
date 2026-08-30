---
id: llm-scrubbing
component: redaction
approach: llm-scrubbing
realizations:
  - {stack: plain-python, template: redaction/llm-scrubbing.plain.py.j2, provides: Mapper}
evidence: {case_ids: [structured-extraction], confidence: low, last_verified: 2026-08-30}
---
Implements llm-scrubbing for redaction, satisfying Mapper.
