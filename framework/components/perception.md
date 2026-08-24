---
id: perception
name: Perception
caps: [representation, retrieval, memory, planning, reasoning, integration]
required_when:
  - always
---
Normalises whatever arrives -- prose, API calls, events, documents, scheduled
triggers -- into something the rest of the system can act on.

Caps everything downstream, and is the most under-invested component in the
taxonomy. A badly parsed table is not recovered by a better reranker or a
better model; the information is already gone. When quality is capped and
nobody knows why, look here first.
