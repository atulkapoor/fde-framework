---
id: llm-extraction
name: Model extraction
complexity: 2
components: [representation]
applies_when: [output_shape == structured]
avoid_when: [interpretability_required == true]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-27}
---
A model decoding raw records into the declared contract.

Split from the prompted-model approach deliberately, because the claim is
narrower than "use a model": this is a *representation* move, it exists only
where there is a contract to decode into, and freeform output has none. An
approach whose applicability differs by component is two approaches wearing
one name, and the seam always shows at the worst moment.

The opening move for extraction before anything has been measured -- the
deterministic path needs coverage nobody has counted and the cascade needs
calibration that does not exist yet. Behind the same Mapper interface the
deterministic path satisfies, so graduating when the numbers arrive is a
swap, not a redesign.

Avoided where interpretability is required: a mapping that cannot say why it
mapped is precisely what that requirement forbids, and the deterministic
path is the interpretable one.
