---
id: latency_budget_ms
type: duration_ms
kind: requirement
asks: "What is the latency budget, at p95, under expected peak load?"
recognises_near: [respond, response, latency, return, answer, complete, within, under]
---
Normalised to milliseconds however it was written. A budget is stated, never
detected -- you can measure a latency, but only a person can tell you what is
acceptable.

Ask for the percentile and the load condition. "Fast" is not a budget, and
neither is an average.
