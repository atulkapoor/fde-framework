---
id: deterministic
name: Deterministic
complexity: 0
components: [representation]
applies_when: [output_shape == structured, output_shape == decision]
avoid_when:
  - output_shape == freeform
  - output_shape == ranking
  - cheap_path_coverage < 0.95
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Entity masters, regular expressions, generated code, explicit mappings.

Where correctness is not negotiable -- mapping a field, deriving a figure,
resolving an identifier -- this is the right tool and a model is not. "The
model will handle it" is the wrong answer in a regulated setting, and it is
usually the wrong answer everywhere else that a rule can be written down.

Right where it covers the work. Where a meaningful share of records carry no
exact identifier, rules alone finish the ones they can and drop the rest
quietly -- which is why coverage is asked rather than assumed.

Cheapest to run, cheapest to explain, and it fails loudly rather than
plausibly. Reach past it only when the mapping genuinely cannot be stated.
