---
id: labelled-metrics
name: Labelled metrics
complexity: 0
components: [evaluation]
applies_when: [output_shape == classification, output_shape == ranking]
avoid_when: [output_shape == freeform, output_shape == structured]
evidence: {case_ids: [churn-scoring], confidence: high, last_verified: 2026-08-21}
---
Precision, recall and their relatives against held-out labels.

Pick the metric from the cost of each error, not from convention. Where a false
negative costs a hundred times a false positive, accuracy is the wrong number
and will look fine while the system fails.
