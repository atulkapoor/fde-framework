---
id: fixed-sequence
name: Fixed sequence
complexity: 0
components: [planning]
applies_when: [always]
avoid_when: [output_shape == decision]
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Steps written in advance, in order, by a person.

Every path is enumerable, so every path can be tested. Cost and latency are
bounded at design time rather than discovered in production. Where the work
genuinely has a fixed shape this is not a lesser option, it is the correct one,
and reaching past it is how a pipeline acquires a control loop it never needed.

The question worth asking is not whether this counts as an agent. It is whether
the next step can depend on the last one in a way nobody enumerated -- and if
it cannot, this is the answer.
