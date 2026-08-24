---
id: field-match
name: Field-level matching
complexity: 0
components: [evaluation]
applies_when: [output_shape == structured]
avoid_when: [output_shape == freeform]
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Compare each field against a verified answer. Exact where the field is exact,
tolerant where it is a date or an amount.

Gives a per-field breakdown rather than one number, which is what tells you
what to build next. Eighty-eight percent accurate says how often you fail; the
shape of the twelve percent says why.
