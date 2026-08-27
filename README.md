# fde — a framework for Forward Deployed Engineers

**fde** is an open-source framework for Forward Deployed Engineers: it takes a
client engagement from a problem statement to a runnable, deployable AI
project — with every decision traced to a fact, and every fact traced to a
source.

Forward deployed engineers arrive with incomplete information, a client who may
not know what they need, and a deadline. This is the tooling for that:
structured discovery and requirements intake, a decision engine that cites its
evidence, and code generation that ends in something you can actually deploy —
including on-premise, inside a customer VPC, or fully air-gapped.

```bash
fde start acme --statement "Extract fields from supplier invoices."
fde ask acme --role admin        # role-scoped discovery interview
fde architect acme               # the design, with cited rationale
fde build acme --out project     # code + evals + deploy assets + runbook
```

---

## Who this is for

- **Forward deployed engineers and solutions engineers** delivering AI systems
  inside client environments, where discovery, deployment constraints and
  handover matter as much as the model.
- **Consultancies and AI delivery teams** who want engagement knowledge to
  compound — every retrospective can enter a shared corpus as an anonymised
  case.
- **Platform teams** shipping LLM systems into regulated, on-premise, or
  air-gapped environments, where "call a hosted API" is not an option and the
  evaluation has to run where the system runs.

## Status: built, unproven

The pipeline exists end to end: intake (prose, documents, sample pairs,
role-scoped interview, hardware scan) → fact log with provenance → permutation
space → gates → decide → architect → build (code, evals, deploy assets,
runbook) → retro and case capture. Overrides are honoured on the next run,
trigger observations feed calibration, and a reviewed case can enter the
corpus.

| | |
|---|---|
| ✅ Working | Registry + validation · fact log · prose/document/sample intake · interview · space pruning · five gates (one hard) · decide with cited evidence · architect · `fde build` emitting a runnable project with evals, deploy and ops assets · hardware scan · costing · evolution capture · a generated `RISKS.md` naming every waived gate and overridden recommendation |
| 🚧 Honest gaps | The evidence corpus is four unpopulated cases (`fde kb gaps` says so) · rule *revision* awaits a corpus with outcomes · `fde kb sweep` lists profile shapes no approach serves |

660+ tests, no production users yet. Treat it as a working system being
hardened in the open — it has survived three adversarial review rounds, and
every defect found is pinned as a regression test.

---

## The idea

Three parts.

**Input** is one operation with several interchangeable surfaces — free-flow
prose, a role-scoped interview, an environment scan, sample input/output pairs,
an inventory of what the client already runs. Each emits a `Fact` into one
`Profile`. No surface is a prerequisite for any other, so an FDE can write prose,
interview a sponsor on Monday and three users on Wednesday, drop in sample files,
and arrive at the same place.

Two rules make that work. **Arrival order never decides anything** — provenance
does, and it is dimension-dependent: a measurement outranks anything said about
the environment, while a stated requirement outranks a measurement, since you
cannot detect a latency *budget*. And **two people disagreeing is a finding, not
a conflict to resolve**; the dimension is left unresolved and reported, because
the gap between what a sponsor believes and what a user experiences is usually
the most valuable thing discovery produces.

**Processing** prunes a space of possibilities as facts arrive, decomposes the
problem into components, and decides an approach, pattern and stack for each —
with cited evidence, ranked rejected alternatives, and a measurable trigger for
when to graduate to something more sophisticated. Five gates stand before
building: verified data access (the one that cannot be waived), a re-measurable
baseline, a named evaluation owner, scope drift against the original statement,
and offline evaluability for air-gapped deployments.

**Output** is a project: code, an evaluation harness seeded from the client's
own examples, deployment artifacts for whichever substrate was actually chosen
(systemd unit, Docker Compose, Kubernetes manifests), approval gates and
critics in front of anything irreversible, and the documents explaining all
three — including a risk page naming every gate that was waived and why.

## What it will not do

**Recommend a tool because it is fashionable.** `plain-python` is a first-class
option in every pattern, and the schema rejects any pattern that omits it. A
two-step linear workflow should not get a graph framework, and the framework has
to be able to say so.

**Reach for a container by default.** Deployment substrate is a ladder from a
systemd unit through to Kubernetes. For a single-node on-prem deployment serving
one model to a team with no container competence, rung zero is the right answer.

**Assume a jurisdiction, sector, topology or stack.** Everything is a discovered
parameter with a sensible default. A locale pack may pre-set values on dimensions
that already exist and attach obligations to the build; it may never introduce a
new dimension, because geography changes what you must produce, not how you
decide.

**Guess.** Every claim carries evidence, a date, and a re-derivation rule. Where
the framework has no evidence, it says so — undecidable components ship as
modules that raise with the reason attached, never as silent gaps.

## Install

```bash
git clone https://github.com/atulkapoor/fde-framework.git
cd fde-framework
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

## Try it

```bash
.venv/bin/fde start acme --statement "Extract fields from supplier invoices."
.venv/bin/fde ask engagements/acme --role admin      # role-scoped interview
.venv/bin/fde status engagements/acme                # gates, gaps, disagreements
.venv/bin/fde architect engagements/acme             # the design, with rationale
.venv/bin/fde build engagements/acme --out project   # refuses until gates clear

.venv/bin/fde scan engagements/acme                  # what this hardware runs
.venv/bin/fde cost --requests-per-day 500000 --model-b 70   # dated fleet sizing

.venv/bin/fde kb validate --root framework   # parse and cross-link the registry
.venv/bin/fde kb gaps     --root framework   # what the corpus is missing
.venv/bin/fde kb sweep    --root framework   # profiles no approach can serve
.venv/bin/pytest -q
```

`kb validate` is strict, because CI runs it and a warning nobody reads is not a
check. `--lenient` exists for the hour when you are mid-way through authoring
content and the links do not resolve yet.

## Design

The registry under `framework/` is data, not code. Adding a stack, a pattern, a
locale or a case is a file, never a change to `src/`. That constraint is enforced
by tests, and it is the thing that keeps the framework general rather than
gradually becoming one consultancy's tooling.

Patterns are separated from stacks because patterns are stable for years and the
libraries implementing them churn in months. A pattern says *what*; one
realization per stack says *how*, as a template plus a claim to satisfy a typed
interface. Swapping the stack changes the emitted code and not the architecture,
and there is a test asserting exactly that.

## FAQ

**What is a Forward Deployed Engineer?**
An engineer who works inside a client's environment to deliver a working
system — part solutions architect, part implementer, part translator between
what a client asks for and what they need. The role is common in AI companies
shipping into enterprises; this framework encodes the craft of running such an
engagement well.

**Does the framework itself call an LLM?**
No. Intake parsing, decision-making and code generation are deterministic —
the same profile always produces the same project, so a diff between two
builds means a decision changed. LLMs appear in the *generated* systems where
the profile justifies one, behind interfaces that make them swappable.

**Does it work air-gapped?**
Yes, by design. The framework runs from plain files with no server or network
dependency, the registry knows which stacks can run inside an air gap, and the
offline-evaluability gate refuses a design whose metric cannot run where the
system runs.

**How is this different from a project template?**
A template gives everyone the same starting point. This decides — from
discovered facts, with cited evidence and named rejected alternatives — and
then generates. Two clients with different constraints get different
architectures, and the document explains why.

**How does it improve over time?**
Every engagement captures its overrides (when the FDE chose differently),
trigger calibration (did predicted graduations fire?), and an anonymised case.
Cases enter the corpus only after human sanitisation review; rules are revised
only when a corpus of outcomes exists — capture now, revise later, never
pretend.

**What does "self-evolving" mean here, concretely?**
Three recorded signals — overrides, trigger observations, case outcomes — and
a human-gated path from a retrospective into the shared knowledge base.
Nothing in `framework/` changes by itself; the corpus grows, and revision
against it is a deliberate, evidenced act.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: contributions enter
against a contract, and **client material never enters this repository** — only
patterns re-expressed in the framework's own words. Sanitisation is enforced in
CI: allowed paths only, history checked, credential and personal-data patterns,
and no unreviewed case can be committed.
