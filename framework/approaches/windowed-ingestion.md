---
id: windowed-ingestion
name: Windowed ingestion
complexity: 1
components: [perception]
applies_when: [input_format == streams]
avoid_when: [input_format == documents, input_format == scanned_documents]
evidence: {case_ids: [route-planning], confidence: medium, last_verified: 2026-08-28}
---
A stream into bounded batches, because nothing downstream reasons over an
infinity.

Perception for input that never ends: consume, window by count or by time
(whichever closes first), stamp each window with what it saw and when, and
hand finite batches to the pipeline. The window is the unit of everything
downstream -- of retry, of idempotency, of evaluation -- so its identity is
stable and its boundaries are recorded.

Late data is the design decision, not an edge case: a watermark says how
long a window waits, and what arrives later lands in a correction window
rather than mutating a closed one. Reprocessing a closed window is how the
same event gets acted on twice.

Avoided for finite corpora: documents want batch ingestion with a
known end, and watermarks on a corpus that does not move are ceremony.
