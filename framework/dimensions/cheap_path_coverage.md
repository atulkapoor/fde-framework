---
id: cheap_path_coverage
type: ratio
scope: non_functional
kind: requirement
weight: 1.0
asks: "What share of records can the exact, rule-based path settle on its own?"
ask_role: [eval_owner, admin]
recognises_near: [have an identifier, exact match, carry a reference, unambiguous]
---
The share of the work a deterministic path can finish without judgement.

This is what decides whether a cascade is worth its complexity. Where nearly
every record carries an exact identifier, rules alone are the answer and a
second tier is machinery nobody needs. Where a meaningful minority does not,
rules alone silently drop those records -- and "we handled the ones we could" is
not a system, it is a partial one with the gap unmeasured.

Measured on real records rather than estimated. The number people guess here is
consistently higher than the number the data shows, because the exceptions are
exactly what nobody remembers.
