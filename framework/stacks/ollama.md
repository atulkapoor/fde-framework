---
id: ollama
name: Ollama
licence: MIT
topologies: [customer-vpc, hybrid, on-prem, air-gapped]
last_verified: 2026-09-01
provides: {ModelServer: stable}
reversibility: cheap
---
The packaged single-box path to local models: one binary, a model library,
and an OpenAI-compatible endpoint on port 11434 that everything this
framework emits already speaks. On Apple silicon it runs on the MLX backend
(0.19+, unified memory 32GB and above), which is why it is the default
recommendation for a laptop or a single workstation.

Not a fleet server: no continuous batching, no paged attention. The moment
there are ten concurrent users, this is the wrong stack and vLLM (or SGLang,
where requests share long prefixes) is the right one -- which is a swap of
realization, not of architecture.
