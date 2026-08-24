---
id: ocr-pipeline
component: perception
approach: ocr-pipeline
realizations:
  - {stack: plain-python, template: perception/ocr-pipeline.plain.py.j2, provides: Parser}
  - {stack: tesseract, template: perception/ocr-pipeline.tesseract.py.j2, provides: Parser}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements ocr-pipeline for perception, satisfying Parser.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
