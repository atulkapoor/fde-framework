---
id: reasoning
name: Reasoning
caps: [integration]
required_when:
  - output_shape == freeform
  - output_shape == decision
---
The model deciding what to do. Chain of thought, ReAct, plan-then-execute,
reflection.

Its real work is two predicates, evaluated repeatedly: **can I answer this
directly, or must I act first?** and **is the goal achieved?** Those are the
only points where the system decides anything; the rest is plumbing. When
agents misbehave in production the fault is usually in how those two checks
were specified, not in the model evaluating them -- so they are specified,
tested and evaluated explicitly rather than left implicit in a prompt.

Every pattern here declares a bound. A loop with no step cap is not a
reasoning pattern, it is an outage waiting for a slow afternoon.
