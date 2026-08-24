---
id: judged
name: Judged
complexity: 2
components: [evaluation]
applies_when: [output_shape == freeform]
avoid_when: [output_shape == structured, output_shape == classification]
evidence: {case_ids: [studio-style], confidence: medium, last_verified: 2026-08-21}
---
A model grades the output against a rubric, calibrated against human agreement
before anyone trusts it.

Two rules. The author never grades itself. And where nothing may leave, the
judge runs locally -- a metric that needs a hosted model is not a metric you
have, and finding that out at deployment is too late.
