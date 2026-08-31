---
id: speech-transcription
component: perception
approach: speech-transcription
realizations:
  - {stack: plain-python, template: perception/speech-transcription.plain.py.j2, provides: Parser}
  - {stack: whisper, template: perception/speech-transcription.whisper.py.j2, provides: Parser}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-09-01}
---
Implements speech-transcription for perception, satisfying Parser.
