---
id: human_waiting
type: enum
kind: requirement
asks: "Is a person waiting for the result?"
values: ["yes", "no", "mixed"]
recognises:
  "no":
    - nobody is waiting
    - no one is waiting
    - runs overnight
    - runs in batch
    - batch job
    - offline process
  "yes":
    - user is waiting
    - interactive
    - real time
    - real-time
  "mixed":
    - both interactive and batch
ask_role: ['user', 'sponsor']
---
Decides how inference is paid for. A person waiting makes a cold start a user
experience problem; nobody waiting makes it an infrastructure detail, and
scale-to-zero compute becomes far cheaper than per-token pricing.

`mixed` is not a fudge: it means the system needs two inference decisions, one
per path.
