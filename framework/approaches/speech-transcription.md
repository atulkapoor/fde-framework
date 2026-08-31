---
id: speech-transcription
name: Speech transcription
complexity: 1
components: [perception]
applies_when: [input_format == audio]
avoid_when: [input_format == documents, input_format == structured_data, input_format == text]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-09-01}
---
Voice to text, before anything downstream reasons about it.

**The word error rate is this modality's version of the OCR ceiling**: no
later component recovers a word that was never heard, and a system quoting
end-to-end accuracy above its transcription accuracy is quoting a number
that cannot exist. Measure it on the client's own audio -- accents, lines,
handsets -- never on a benchmark's studio recordings.

Where the callers speak several languages, the transcription model is the
first place that requirement lands, and per-language error rates belong in
the acceptance protocol -- an average across languages hides exactly the
population the service was built to reach.
