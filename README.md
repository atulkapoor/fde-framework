# fde

A framework that takes an engagement from a problem statement to a runnable,
deployable project — with every decision traced to a fact, and every fact traced
to a source.

Forward deployed engineers arrive with incomplete information, a client who may
not know what they need, and a deadline. This is the tooling for that: structured
intake, a decision engine that cites its evidence, and code generation that ends
in something you can actually deploy.

---

## Status: early

The substrate works. Most of the pipeline does not exist yet.

| | |
|---|---|
| ✅ Working | Registry schemas · markdown+YAML loader with located errors · cross-link validation · gap detection · `fde kb` |
| 🚧 Next | Fact log · prose intake · the permutation space · role-scoped interview |
| 📋 Designed, unbuilt | Decide · architect · build · evals · deploy · evolution capture |

90 tests, no production users. Treat it as a design being built in the open
rather than something to adopt.

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
when to graduate to something more sophisticated.

**Output** is a project: code, an evaluation harness seeded from the client's own
examples, deployment artifacts for whichever substrate was actually chosen, and
the documents explaining all three.

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
the framework has no evidence, it says so.

## Install

```bash
git clone https://github.com/atulkapoor/fde-framework.git
cd fde-framework
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

## Try what exists

```bash
.venv/bin/fde kb validate --root framework   # parse and cross-link the registry
.venv/bin/fde kb gaps     --root framework   # what the corpus is missing
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: contributions enter
against a contract, and **client material never enters this repository** — only
patterns re-expressed in the framework's own words.
