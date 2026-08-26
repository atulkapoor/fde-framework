---
id: llm
name: Prompted model
complexity: 2
components: [reasoning, representation]
applies_when: [output_shape == freeform, output_shape == structured]
avoid_when: [output_shape == classification, output_shape == decision]
evidence: {case_ids: [studio-style], confidence: medium, last_verified: 2026-08-21}
---
A capable model, prompted, with no adaptation.

The right first move for open-ended generation, and the fastest thing to stand
up. Try it before fine-tuning: the gap it leaves is what tells you whether
adaptation is worth its cost.

The same holds for structured output, where the model decodes into a declared
schema. This is the standard opening move for extraction before anything has
been measured -- the cascade needs calibration that does not exist yet, and
the deterministic path needs coverage nobody has counted. Start here, measure,
then graduate.

Swapping the model rarely fixes a wrong answer -- it changes the tone of the
wrong answer. When quality is capped, look upstream at what the model was given.
