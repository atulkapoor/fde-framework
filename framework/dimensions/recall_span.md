---
id: recall_span
type: enum
scope: functional
kind: requirement
weight: 0.5
asks: "How far back does the system need to remember?"
ask_role: [user, eval_owner, admin]
values: [within_turn, within_session, across_sessions]
recognises:
  within_turn: [no memory, each request is independent, stateless]
  within_session: [remember the conversation, within the chat, during the session]
  across_sessions: [remember me next time, learn from past, build up over time, remembers previous]
---
Short-term and long-term memory are two systems, not one.

They differ in write policy, in how they are read back, and in how they fail. A
mistake in working state disappears at the end of the session; the same mistake
written to a long-term store is permanent, and will be recalled confidently
forever. Collapsing them is a cheap decision with an expensive tail.

Memory of regulated data inherits that data's residency, embeddings included.
