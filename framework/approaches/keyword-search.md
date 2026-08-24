---
id: keyword-search
name: Keyword search
complexity: 0
components: [retrieval]
applies_when: [query_pattern == lookup]
avoid_when: [query_pattern == multi_hop]
evidence: {case_ids: [structured-extraction], confidence: high, last_verified: 2026-08-21}
---
Lexical matching. Unfashionable, cheap, and hard to beat when people search for
terms that actually appear -- identifiers, part numbers, names.
