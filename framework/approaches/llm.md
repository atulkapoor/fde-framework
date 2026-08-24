---
id: llm
name: Prompted model
complexity: 2
components: [reasoning]
applies_when: [output_shape == freeform]
avoid_when: [output_shape == structured, output_shape == classification, output_shape == decision]
evidence: {case_ids: [studio-style], confidence: medium, last_verified: 2026-08-21}
---
A capable model, prompted, with no adaptation.

The right first move for open-ended generation, and the fastest thing to stand
up. Try it before fine-tuning: the gap it leaves is what tells you whether
adaptation is worth its cost.

Swapping the model rarely fixes a wrong answer -- it changes the tone of the
wrong answer. When quality is capped, look upstream at what the model was given.
