---
id: supermemory
name: Supermemory
licence: MIT
topologies: [managed-api, public-saas, customer-vpc, hybrid, on-prem]
last_verified: 2026-09-18
provides: {Store: stable}
reversibility: expensive
---
A memory engine rather than a memory table: it extracts facts from what it
is given, resolves contradictions over time, builds a profile per container
tag, and forgets on its own -- the three problems the no-framework
episodic store solves by hand. Ships as one local binary on port 6767
speaking the same API as its hosted service, with a local embedding model
by default, so nothing has to leave the building to use it.

Earn it the same way as any second stateful system: offered when the
profile already runs it, because a memory store holds client data by
definition and inherits residency -- the emitted realization refuses the
hosted endpoint outright behind a data boundary. Not offered air-gapped
yet: the local binary fetches its embedding model on first boot, which
has to be staged by hand inside an air gap before this can be verified
there. The Python SDK is Apache-2.0; the emitted code needs neither it
nor any dependency -- the API is two POSTs.
