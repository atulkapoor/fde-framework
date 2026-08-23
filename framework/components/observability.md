---
id: observability
name: Observability
caps: []
required_when: ["always -- a loop cannot be debugged one node at a time"]
---
Traces, cost and latency attribution, trajectory capture.

Spans the whole system because a loop is not debuggable by inspecting a single
node. You need the trajectory: what it decided, in what order, and why it
stopped.
