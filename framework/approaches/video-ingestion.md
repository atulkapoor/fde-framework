---
id: video-ingestion
name: Video ingestion
complexity: 2
components: [perception]
applies_when: [input_format == video]
avoid_when: [input_format == documents, input_format == structured_data, input_format == text]
evidence: {case_ids: [structured-extraction], confidence: low, last_verified: 2026-09-01}
---
Frames sampled from footage, timestamped, and handed on as images -- video
perception is image perception plus the decision of which moments to look at.

Complexity 2 because the sampling policy is a real design surface: too
sparse misses the event, too dense drowns the pipeline, and the honest
starting point is event-triggered sampling around whatever the stream layer
flags rather than a fixed frame rate nobody can justify.
