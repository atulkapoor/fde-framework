---
id: redaction
name: Redaction
caps: [representation, embedding, retrieval, memory, reasoning, integration]
required_when:
  - sensitivity_present == true and data_residency == may_leave
---
Masks the fields that would hurt if they left, so what leaves is the record
without them rather than the record or nothing.

Exists only in the crossed case: data free to leave, sensitive fields inside
it. Where nothing may leave, the boundary already holds everything and a
masking step is weight without work; where nothing is sensitive, there is
nothing to mask.

Sits after perception and before everything downstream, because a mask
applied after embedding is a mask applied to a copy -- the vector already
remembers the name.
