---
id: classical-ml
name: Classical ML
complexity: 1
components: [representation, reasoning]
applies_when: [output_shape == classification and labelled_count > 0, output_shape == ranking and labelled_count > 0]
avoid_when: [output_shape == freeform, output_shape == structured]
evidence: {case_ids: [churn-scoring], confidence: high, last_verified: 2026-08-21}
---
Gradient-boosted trees and their relatives on tabular data.

Still the right answer for a numeric or class outcome from columns, and it wins
on the three axes that usually decide: it trains on far less data, it answers in
single-digit milliseconds, and it can say which features moved the prediction.

That last one is often decisive rather than nice to have. A requirement to
explain a decision to a regulator rules out approaches that cannot produce a
reason, whatever their accuracy.
