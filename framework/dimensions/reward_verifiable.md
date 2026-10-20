---
id: reward_verifiable
type: enum
scope: data
kind: requirement
weight: 1.0
asks: "Can a task's outcome be checked automatically -- a pass/fail nobody has to judge?"
values: ["yes", "no", "partly"]
recognises:
  "yes":
    - automatic pass/fail
    - automatically checked
    - checked automatically
    - verified automatically
    - a test tells us
    - the tests tell us
    - unit tests decide
    - ground truth is known
    - the answer is known
    - exact answer
    - we can check the result
    - can be checked mechanically
  "no":
    - judged by a person
    - a person judges
    - a reviewer decides
    - no ground truth
    - matter of judgement
    - matter of judgment
    - subjective
  "partly":
    - partly checkable
    - some can be checked
ask_role: ['eval_owner', 'admin']
---
Whether a task's result can be scored without a person: a spreadsheet
that either matches or does not, a migration that either runs or does
not, a retrosynthesis that either reaches the target or does not --
against an answer written by a reviewer who has to be asked each time.

The question decides more than the evaluation. With an automatic reward
and enough tasks, the design of an agent's harness stops being a decision
made from facts and becomes a search: candidate harnesses run against
the tasks, and the numbers choose. Work published in 2026 went further
and moved an evolved harness into a small model's weights, deploying it
with one tool. None of that is available without the reward, and this is
the fact that says whether it is. Without one, the judge is a person or a
calibrated model, and the exam is the client's verified pairs.

What acts on it today: a judged evaluation is avoided where the outcome
can be checked automatically -- the check is the metric, and a judge in
front of it is a weaker instrument standing in for a comparison. The
harness-search and distillation paths wait for production evidence.

Asked of the person who owns the evaluation, because "we have tests" from
an engineer usually means the code has tests, not that the task's
outcome does. The gap between the two is the whole question.
