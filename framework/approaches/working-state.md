---
id: working-state
name: Working state
complexity: 0
components: [memory]
applies_when: [recall_span == within_session, recall_span == within_turn]
avoid_when: [recall_span == across_sessions]
evidence: {case_ids: [studio-style], confidence: high, last_verified: 2026-08-21}
---
Context held for the length of a session and then discarded.

Cheap, and it fails safely: a mistake in working state disappears when the
session ends. Nothing here is a decision anyone has to live with.
