---
id: deterministic-masking
name: Deterministic masking
complexity: 0
components: [redaction]
applies_when: [sensitivity_present == true]
avoid_when: [sensitivity_present == false]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-30}
---
Named fields replaced by stable hashes, before anything downstream sees the
record.

Deterministic on purpose, twice over. The same value masks to the same token,
so joins and deduplication survive masking -- a random mask would quietly
break every downstream equality. And the field list is declared, not
detected: a model guessing which fields are sensitive is a model that will
one day guess wrong in the direction that matters, so the list comes from the
contract the client's own samples marked and the FDE confirmed.
