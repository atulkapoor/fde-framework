# Declined, and why

Seventeen outside readings have shaped this framework, and the ones
worth the most found defects reproducible from the public source. The
same readings also proposed features, and several of those have been
proposed four and five times. Each is recorded here once, with its
reason and the release that declined it, so the next proposal of the
same thing is answered by this file rather than by silence.

## The bar

An idea is taken up when one of two things is true:

1. **A person using the framework on a real workflow hit the need.** Not
   a reviewer imagining a user; a user. The framework has none yet
   beyond its author, and the README says so.
2. **An outside reading found a defect reproducible from the public
   source.** A traceback, a wrong number, a contract the exam cannot
   reach, a boundary the agent can cross. These are fixed the same day,
   as a check before a fix, and the changelog names the reading.

A proposal that is neither is declined and recorded below. A proposal
that was declined and is proposed again with a user attached is a new
proposal.

## Declined

| Idea | Why | Release |
|---|---|---|
| `fde explain`: a plain-language explanation of a recommendation | `fde architect` prints each decision with its reason and its rejected alternatives; `fde next` says what turns on the next question; `fde report` carries both. A third command that re-explains would be the second place for the same words. | 0.1.44 |
| `fde compare`: candidate architectures side by side on value, effort, cost, risk | The rejected-alternatives section of the design is that comparison, per component, with the fact each rejection turns on. The columns proposed (value, effort, cost) are the figures the framework refuses to estimate without a baseline. | 0.1.45 |
| `fde demo`: a synthetic guided engagement, no data, no keys | The four public demos are real data, end to end, with every refusal preserved, and the README's first screen is a two-minute walk with nothing but `pip install`. A synthetic run that ends green would be the one demonstration the framework does not stand behind. | 0.1.45, 0.1.46 |
| Bigger starter examples: more pairs, edge cases, holdouts | The worked examples ship three pairs on purpose and say that a golden set below forty measures the examples rather than the system. The benchmarks are the demos. | 0.1.48 |
| Wire OCR into the invoice example | Wiring an engine is what `fde implement` does, with a coding agent, against the holdout, inside the fence. An example that ships it wired would be an example of the author having done the engagement. | 0.1.48 |
| A synthetic policy corpus so the retrieval example scores by default | A score on a corpus the author wrote, against questions the author wrote, is the number the calibration gate exists to refuse. The rfc-qa demo is the real one, and it refused its own judge. | 0.1.48 |
| A hosted dashboard, a visual decision explorer, a platform | No user has asked to see the record somewhere other than the record. A dashboard before a second user is a demo of a dashboard. | 0.1.44, 0.1.46 |
| Plugins, orchestration adapters, issue-tracker and CI connectors | The one integration that reaches people where they work is the coding agent, and that is `fde mcp` and the skill. Every further adapter is a surface that must be kept honest with no one on the other side of it. | 0.1.44 |
| Serving `build`, `implement` or `deploy` to the coding agent over MCP | A build is a person's act, after eight gates, at their terminal, with their name on the attestations. An agent that can build is an agent that can waive. | 0.1.41 |
| Instrumenting the framework's own overhead: time per stage, user actions, abandonment | The record already carries every timestamp; the figures can be computed the day there are engagements to compute them over. Instrumenting the author measuring the author is a number with one data point. | 0.1.45 |
| A held-out benchmark corpus with expected answers | Expected answers chosen by the framework's author alone are not held out from the framework's author. The corpus needs outside contributors; `EXPERIMENT.md` is the protocol it would run to. | 0.1.45 |
| Splitting `emit.py` and `cli.py` | They are large. They are also where every pinned finding lives, and a split with no change asked for is churn under the same tests. The day a change needs a seam, the seam gets cut there. | 0.1.47 |
| More architecture patterns, to grow the corpus | A pattern enters the registry from a documented production deployment or a retrospective, with its evidence. Patterns added to raise a count are the count. | 0.1.44 |
| A test count as a headline | It is stated once, in the claim ladder, beside what it does and does not prove. | 0.1.44 |
| Asking for stars as the call to action | The call to action is to run the two-minute walk, challenge a demo, or bring a workflow. Stars are not a measurement of any of those. | throughout |
