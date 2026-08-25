---
id: explainability-record
name: Explainability record
complexity: 1
components: [accountability]
applies_when: [interpretability_required == true]
avoid_when: [interpretability_required == false]
evidence: {case_ids: [churn-scoring], confidence: high, last_verified: 2026-08-21}
---
Every decision keeps what drove it, in a form somebody outside the team can read
months later.

Built in from the start or not at all: reconstructing why a model decided
something after the fact is guesswork wearing a report's formatting.
