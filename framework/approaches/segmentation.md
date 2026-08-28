---
id: segmentation
name: Segmentation
complexity: 1
components: [representation]
applies_when: [output_shape == freeform]
avoid_when: [output_shape == structured]
evidence: {case_ids: [studio-style], confidence: medium, last_verified: 2026-08-28}
---
Documents into retrievable chunks, with their origins attached.

The representation a freeform system actually needs: not fields onto a
contract but a corpus cut into pieces a retriever can rank -- windows sized
for the questions people ask, overlapping so answers that straddle a cut are
not lost, each chunk carrying its source and offsets so every generated
sentence can point back at where it came from.

Traceability is the non-negotiable half. A chunk that cannot say where it
came from produces answers that cannot be checked, and an unverifiable
answer from a system inside a client's environment is a liability wearing a
feature's clothes.

Boring on purpose. Semantic and layout-aware splitting are graduations to
earn with measured retrieval quality, not defaults -- fixed windows with
overlap are the rung that ships this week and measures honestly.

Avoided for structured output: chunking an extraction corpus buries
the fields the contract needs under retrieval units nobody asked for --
that shape wants a mapper.
