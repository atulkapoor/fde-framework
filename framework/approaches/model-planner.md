---
id: model-planner
name: Model planner
complexity: 3
components: [planning]
applies_when: [output_shape == decision, recall_span == across_sessions]
avoid_when: [interpretability_required == true]
evidence: {case_ids: [route-planning], confidence: low, last_verified: 2026-08-21}
---
The model decomposes the goal at run time and chooses what to do next.

This is the line worth drawing. Once the next step can depend on the last in a
way nobody enumerated, paths stop being testable and cost stops being bounded --
so crossing it obliges three things a fixed sequence never needed: a step cap, a
budget cap, and a critic before anything irreversible.

Ruled out where a decision must be explained. A plan invented at run time is
hard to defend afterwards, and "the model decided" is not a reason a regulator
accepts.
