---
id: llm-scrubbing
name: Model-assisted scrubbing
complexity: 2
components: [redaction]
applies_when: [sensitivity_present == true]
avoid_when: [sensitivity_present == false, data_residency == cannot_leave]
evidence: {case_ids: [structured-extraction], confidence: low, last_verified: 2026-08-30}
---
A model rewrites free text with the identifying entities removed, for the
case field-level masking cannot reach: a name living *inside* a narrative
field, not in a field of its own.

Never the first decision -- deterministic masking is simpler and wins where
the sensitive material is field-shaped, which is the common case and the
measurable one. Reached by override when the sample pairs show identifiers
inside prose, and carrying its own irony to manage: the scrubbing model sees
the unscrubbed text, so on a boundary engagement it must run inside -- and
where data cannot leave at all, the boundary already holds everything and
this approach is avoided outright.
