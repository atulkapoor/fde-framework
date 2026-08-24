---
id: ocr-pipeline
name: OCR pipeline
complexity: 2
components: [perception]
applies_when: [input_format == scanned_documents, input_format == images]
avoid_when: [input_format == structured_data, input_format == text]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Pixels to text, with everything that implies: confidence per character, layout
inference, and a per-page error rate that becomes the system's ceiling.

Measure that rate before promising anything downstream of it.
