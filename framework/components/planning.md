---
id: planning
name: Planning
caps: [integration, reasoning]
required_when:
  - output_shape == decision
---
Decomposing a goal into ordered subtasks.

Routinely skipped in a prototype and retrofitted painfully once tasks stop
fitting in one hop. The retrofit is expensive because planning changes the
shape of the loop rather than adding a step to it.

A plan chosen at runtime is what makes execution paths unenumerable, which is
what obliges a step bound and a critic. See `reasoning`.
