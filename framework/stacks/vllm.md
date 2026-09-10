---
id: vllm
name: vLLM
licence: Apache-2.0
topologies: [customer-vpc, on-prem, air-gapped, hybrid]
last_verified: 2026-09-10
reversibility: moderate
---
Serving open weights. Continuous batching and prefix caching by default.

What the defaults buy: the KV cache is paged rather than allocated as one
contiguous block per request, so memory fragments less and admits more
concurrent sequences; and the scheduler adds and retires requests mid-batch
instead of waiting for a batch to drain. Together they are why this engine
holds throughput when requests overlap -- and why a sequential single-box
runtime that benchmarked fine at one user falls over at twenty.

The flip side is operational: vLLM is a service somebody runs (CUDA stack,
versioned kernels), where the single-box path is one binary. The crossover
is measured, not guessed: the arrival rate the engagement recorded says
whether requests overlap, and `fde scan <engagement>` reads it.
