---
id: observability
name: Observability
caps: []
pipeline: false
required_when:
  - always
---
Traces, cost and latency attribution, trajectory capture.

Spans the whole system because a loop is not debuggable by inspecting a single
node. You need the trajectory: what it decided, in what order, and why it
stopped.
