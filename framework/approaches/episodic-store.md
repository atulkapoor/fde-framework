---
id: episodic-store
name: Episodic store
complexity: 2
components: [memory]
applies_when: [recall_span == across_sessions]
avoid_when: [recall_span == within_turn, recall_span == within_session]
evidence: {case_ids: [studio-style], confidence: medium, last_verified: 2026-08-21}
---
What the system learned, kept beyond the session that produced it.

A different system from working state, with a different write policy, and it
fails differently: a wrong belief written here is permanent and will be recalled
with confidence. What gets promoted from working state to long-term is the
decision that matters, and it should be deliberate rather than automatic.

Holds client data by definition, so it inherits residency -- embeddings too.
