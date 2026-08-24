---
id: deterministic
name: Deterministic
complexity: 0
components: [representation]
applies_when: [output_shape == structured]
avoid_when: [output_shape == freeform, output_shape == ranking]
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Entity masters, regular expressions, generated code, explicit mappings.

Where correctness is not negotiable -- mapping a field, deriving a figure,
resolving an identifier -- this is the right tool and a model is not. "The
model will handle it" is the wrong answer in a regulated setting, and it is
usually the wrong answer everywhere else that a rule can be written down.

Cheapest to run, cheapest to explain, and it fails loudly rather than
plausibly. Reach past it only when the mapping genuinely cannot be stated.
