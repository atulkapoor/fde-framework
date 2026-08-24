---
id: traced
name: Distributed tracing
complexity: 1
components: [observability]
applies_when: [always]
avoid_when: [external_systems < 2]
evidence: {case_ids: [studio-style], confidence: high, last_verified: 2026-08-21}
---
One system with an enumerable path does not need spans across it; structured
logs answer the same questions for less. Past that, spans across the whole path, with cost and latency attributed per tenant.

A loop cannot be debugged one node at a time. You need the trajectory: what it
decided, in what order, and why it stopped -- which is precisely what a log line
per step cannot tell you.

Per-tenant cost attribution is an architectural decision rather than a reporting
one. Retrofitting it means touching every call site.

The GenAI semantic conventions are **not stable**: every attribute still carries
development status, and they moved to their own repository on their own release
cadence in mid-2026 -- a separate cadence, not a graduation. Chat and embedding
attributes are settled enough to build on; agent and tool-orchestration ones are
still moving. Use them, pin the version, and expect a rename to arrive as work.
