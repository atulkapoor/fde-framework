---
id: data_residency
type: enum
kind: requirement
asks: "Can client data leave their environment?"
values: [cannot_leave, may_leave]
boundary_when: [cannot_leave]
recognises:
  cannot_leave:
    - data cannot leave
    - data can't leave
    - data must not leave
    - data never leaves
    - cannot leave the client
    - cannot leave our
    - must stay on-premise
    - must stay on prem
    - no data leaves
  may_leave:
    - data may leave
    - no residency requirement
prunes:
  cannot_leave:
    hosting: [public-saas, managed-api]
ask_role: ['admin', 'sponsor']
---
The single most decisive dimension in most engagements: it prunes more of the
space than anything else, and it is the one an FDE should raise unprompted
rather than wait to be told.

Phrases are anchored on the word "data" on purpose. "I cannot leave the
meeting" is not a residency constraint, and a parser that guesses produces a
wrong fact at artifact strength -- which then outranks the interview answer
that would have corrected it.
