---
id: video-ingestion
component: perception
approach: video-ingestion
realizations:
  - {stack: plain-python, template: perception/video-ingestion.plain.py.j2, provides: Parser}
evidence: {case_ids: [structured-extraction], confidence: low, last_verified: 2026-09-01}
---
Implements video-ingestion for perception, satisfying Parser.
