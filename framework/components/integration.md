---
id: integration
name: Integration
caps: []
required_when:
  - output_shape == decision
  - external_systems > 0
---
Where the system acts on the world: tool calls, APIs, code execution, writes.

Every tool declares whether it is mutative. That single flag is what lets the
autonomy move find the places that need an approval gate and an idempotency
key, without anyone remembering to add them.
