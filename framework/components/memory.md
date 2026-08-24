---
id: memory
name: Memory
caps: [planning, reasoning]
required_when:
  - recall_span == within_session
  - recall_span == across_sessions
---
State the system accumulates from its own operation. Distinct from retrieval:
retrieval reads a corpus somebody else wrote, memory writes what this system
learned.

**Short and long term are two systems, not one.** Short term holds conversation
context and working state; long term holds episodic records and learned
patterns. They differ in write policy, in retrieval logic and in how they fail,
and collapsing them is a common and expensive mistake -- a working-state bug
becomes a permanent one the moment it is written to long-term store.

Memory of regulated data inherits that data's residency. An embedding is not
anonymised, so a memory store holding embeddings of personal data is in scope
for the boundary.
