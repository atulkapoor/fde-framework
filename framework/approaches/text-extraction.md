---
id: text-extraction
name: Text extraction
complexity: 1
components: [perception]
applies_when: [input_format == documents, input_format == text]
avoid_when: [input_format == scanned_documents, input_format == structured_data]
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Pulling text and layout out of documents that already carry a text layer.

Where the ceiling gets set. Tables are the usual casualty: a table flattened
into a line of numbers has lost the relationship between them, and nothing
downstream puts it back.
