<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
  <img src="assets/banner-light.svg" alt="fde — a framework for Forward Deployed Engineers" width="760">
</picture>

# fde — a framework for Forward Deployed Engineers

[![CI](https://github.com/atulkapoor/fde-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/atulkapoor/fde-framework/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Status](https://img.shields.io/badge/status-alpha-orange)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

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

## What it does

| | |
|---|---|
| **Discovery that compounds** | Prose, PDFs, sample pairs, a role-scoped interview and a hardware scan all feed one profile — provenance decides conflicts, never arrival order, and disagreement between people is surfaced as a finding |
| **Gates before building** | Seven checks with remedies; verified data access cannot be waived, and every waiver ships in the project's `RISKS.md` with its reason |
| **Decisions with receipts** | Simplest applicable approach per component, cited evidence, named rejected alternatives — and `fde override` records your call and honours it on every later run |
| **A real project out** | Pipeline in topological order, fail-closed approval gates and critics, an eval harness CI can gate on, deploy assets for the substrate that was actually earned, runbook, SLOs, teardown |
| **Deterministic by design** | The decision path never calls an LLM: same profile, byte-identical project — a diff between builds means a decision changed. Model assistance exists only as opt-in commands, and the boundary doctrine governs them |
| **Jurisdiction as data** | Locale packs preset answers at the weakest provenance and attach dated compliance obligations to the build; they can never change how decisions are made |
| **Self-evolution, honestly** | Overrides, trigger calibration and anonymised cases are captured per engagement; the corpus grows only through human-reviewed ingestion |

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

Those are different claims, and the difference is the point.

**Built**: the pipeline exists end to end — intake (prose, documents, sample
pairs, role-scoped interview, hardware scan) → fact log with provenance →
permutation space → seven gates → decide → architect → build (code, evals,
deploy and ops assets, `RISKS.md`, `COMPLIANCE.md`) → retro and case
capture. Overrides are honoured on the next run, trigger observations feed
calibration, and a reviewed case can enter the corpus. over 800 tests; three
adversarial review rounds (108 findings, each fixed and pinned as a
regression test); CI gates on the suite, lint, and a sanitisation scan of
the tree *and its history*; the evidence corpus is anchored to publicly
documented production deployments; every decision is reproducible from its
inputs.

**Unproven** means exactly one thing: no production engagement has yet run
through it start to finish. The proof loop is wired and waiting — `fde
retro` captures measured outcomes, human-reviewed cases grow the corpus,
and rule *revision* begins when there are retrospectives to revise against,
not before. Pretending earlier would be borrowing rigour rather than having
it.

What that means for you today: the generated projects are real and the
decisions are defensible, but you are an early adopter, not a reference
customer — and the first measured retrospectives will be worth more to this
framework than any feature.

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
when to graduate to something more sophisticated. Seven gates stand before
building: verified data access (the one that cannot be waived), a re-measurable
baseline, a named evaluation owner, scope drift against the original statement,
offline evaluability for air-gapped deployments, licence compatibility
against what the client intends to ship, and a client security review wherever
the system lives in their environment or touches their systems.

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

Prerequisites: Python 3.11+ and git. Not yet on PyPI — install from source:

```bash
git clone https://github.com/atulkapoor/fde-framework.git
cd fde-framework
python3 --version   # must say 3.11+; an older python3 makes pip backtrack for ages instead of failing fast
python3 -m venv .venv && .venv/bin/pip install -e ".[dev,documents]"  # add ,llm for the hosted-model reader path
```

Or with [uv](https://docs.astral.sh/uv/): `uv venv && uv pip install -e ".[dev,documents]"`

### Optional extras

| Extra | Installs | For |
|---|---|---|
| `documents` | pypdf, python-docx | `fde frame --file brief.pdf` — PDF and Word intake |
| `dev` | pytest, ruff | running the test suite and linter |

The core needs none of them: plain-text intake, the decision engine and the
build work with zero optional dependencies, which is deliberate — an
air-gapped install should not drag in what it will not use. A missing reader
refuses by name and says exactly what to install.

### File types

| Intake | Formats |
|---|---|
| Read as text | `.txt` `.md` `.rst` `.csv` `.json` `.yaml` |
| With `documents` extra | `.pdf` `.docx` |
| Refused by name | `.doc` `.pptx` `.xlsx` (and anything unrecognised) — reading a container's bytes as text produces facts from noise, which is worse than reading nothing |
| Sample pairs | `.jsonl` — `{"id", "input", "output", "verified"}` per line |

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

A complete worked engagement — real transcript, synthetic client — lives in
[examples/invoice-extraction](examples/invoice-extraction/).

## What a build emits

```
project/
├── app/                  # components, pipeline, controls, boundary check
│   ├── components/       #   implementations or honest scaffolds — never silent gaps
│   ├── pipeline.py       #   topological order; approval gates before anything mutative
│   ├── controls.py       #   fail-closed: an unwired gate refuses, loudly
│   ├── boundary.py       #   imported at startup when data may not leave
│   ├── contract.py       #   RefusedInput: forbidden input is refused, never guessed at
│   └── llm.py            #   the one model touchpoint, when a decision needs one (boundary-gated)
├── evals/                # golden / edge / adversarial sets from the client's own pairs
│   ├── harness.py        #   fails CI until implemented; judge-based when the evaluation decided judged
│   ├── acceptance.md     #   blind UAT protocol for the client's own judges
│   └── load.py           #   p95 against the stated budget (when one was stated)
├── deploy/               # the substrate that was earned + TEARDOWN.md for all of it
├── ops/                  # runbook keyed to the failure taxonomy, SLOs, rollback
├── ARCHITECTURE.md       # scope read-out, decisions, tools & alternatives, agent posture
├── RISKS.md              # every waived gate and overridden recommendation
└── COMPLIANCE.md         # jurisdiction obligations, when a locale pack was applied
```

## Common commands

| | |
|---|---|
| `fde start <name> --statement "..."` | begin an engagement |
| `fde frame <eng> --file brief.pdf` | prose or documents → facts, played back for correction |
| `fde frame <eng> --reader llm --endpoint http://localhost:11434` | a local model proposes what the deterministic reader missed, at weakest provenance |
| `fde samples <eng> --file pairs.jsonl` | input/output pairs → contract, metrics, golden set |
| `fde ask <eng> --role admin` | role-scoped interview, ordered by what changes the design |
| `fde ask <eng> --role admin --scope non_functional` | one scope axis at a time — the dedicated NFR pass |
| `fde scan <eng>` | measure the hardware, and get a local-model plan sized to it (runtime, judge, coder) |
| `fde status <eng>` | gates, gaps, waivers, disagreements |
| `fde baseline / data-access / security-review / waive / restate` | satisfy or knowingly waive a gate |
| `fde cost --price-per-seat 25 --workflows-per-day 8` | unit economics: whether a seat earns more than it burns, with the levers priced |
| `fde samples <eng> --file pairs.jsonl --sensitive <field>` | golden/edge/adversarial evals from the client's own pairs, sensitive fields marked |
| `fde kb suggest --file brief.md --endpoint http://localhost:11434` | mine a brief for recogniser gaps — proposed, never applied |
| `fde kb export-training <eng> --out train.jsonl` | (brief, facts) pairs — the fine-tune flywheel, kept with the engagement |
| `fde reuse <eng> <stack>` | record what the client already operates, so reuse can beat adoption |
| `fde locale <eng> eu-gdpr` | jurisdiction pack: presets plus obligations emitted as COMPLIANCE.md |
| `fde architect <eng>` | the design, rationale and rejections |
| `fde build <eng> --out project` | emit; refuses while gates block |
| `fde implement project/` | drive a coding agent until the emitted evals pass, inside guardrails |
| `fde triage --statement "..." --statement "..."` | rank candidate problems by what discovery can already decide |
| `fde override --component X --choose Y --because "..."` | your call, recorded and honoured |
| `fde observe / retro` | record trigger firings; capture the case |
| `fde cost --requests-per-day N --model-b B` | dated fleet sizing |
| `fde kb validate / gaps / sweep` | registry health, work items, dead zones |

## Troubleshooting

**`no registry here`** — the default `--registry framework` is relative; run
from the repository root or pass the path.

**`build` refuses with gates listed** — that is the point. `fde status`
names each gate and its remedy; soft gates take `fde waive <gate> --reason`,
data access takes only credentials that returned real rows.

**A component module raises `UndecidedComponent`** — nothing could be
decided for it; the raise message names the unanswered question. Answer it
and rebuild — holes are loud here, never silent.

**`fde kb sweep` shows undecidable profiles** — some are honest
contradictions (data cannot leave + nobody to operate). `fde architect` on
that profile names the conflicting facts.

**The evaluation harness fails CI** — it evaluates the emitted pipeline;
it fails until the components are implemented end to end. A gate that
cannot say no is not a gate.

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

## Privacy

Everything runs from plain files on your machine. The default path makes **no
network calls, has no telemetry, and never transmits engagement content
anywhere** — it works on a plane and inside an air gap, and a text editor is
always a legal way into its state. Discovery, decisions, and builds never call
an LLM.

Four commands are the deliberate exceptions, each opt-in and each governed by
the framework's own boundary doctrine: `fde frame --reader llm` (a model
proposes facts, at the weakest provenance — refused to hosted models unless the
engagement states data may leave; local endpoints always allowed), `fde kb
suggest` (mines a brief for recogniser gaps under the same rule, proposing —
never applying — vocabulary), `fde implement` (drives a coding agent you
name), and the judge-based eval harness in *generated* projects whose
evaluation decided `judged` (configured by `LLM_ENDPOINT`, hosted path refused
inside a boundary). Nothing calls a model silently, and `fde scan` recommends
a local model sized to your hardware so none of it needs to leave the machine.
The LLM is everywhere as a **proposer**; the decision path stays
deterministic, because fingerprints, byte-identical rebuilds and an
accountable RISKS.md are the product. Fine-tuning follows the corpus's own
client rule: `fde kb export-training` builds the (brief, facts) corpus from
retained briefs, and a fine-tuned reader earns adoption when the pairs number
in the thousands *and* the measured base-model hit rate falls short.

Engagement directories (client facts, baselines, gate state) are excluded
from version control by construction and enforced in CI — along with
credential patterns, personal-data patterns, and a check that no unreviewed
case can ever be committed.

## Team setup

The registry is the shared asset; engagements are private working state.

- **Share `framework/`** — fork or clone it as your team's knowledge base.
  Every dimension, approach, stack and case is a markdown file; review
  registry changes like code, because they decide architectures.
- **Never commit `engagements/`** — client facts stay local. The repository's
  own `.gitignore` and CI sanitisation gate enforce this shape; keep it in
  yours.
- **Grow the corpus deliberately** — `fde retro` captures a case,
  `fde kb ingest-case` lands it as `sanitization: pending`, a human reviews
  it for anything identifying, and only `reviewed` cases can be committed.
  One reviewed case per delivered engagement compounds fast.

## Roadmap

- **Rule revision from outcomes** — capture is wired end to end; revision
  deliberately waits for a corpus of measured retrospectives rather than
  pretending a handful is evidence.
- **PyPI release** — after the first tagged version.
- **More locale packs and stacks** — both are data; contributions enter
  against [CONTRIBUTING.md](CONTRIBUTING.md)'s contract.
- **Language, channel, and device axes** — six of twenty industry test
  statements named regional languages, low bandwidth, or basic devices;
  the honest wiring (per-language evaluation, SMS/IVR serving approaches,
  safeguarding governance) is a corpus milestone, not a checkbox.
- **Scale words** — "millions of applications", "tens of millions of
  players": refusing to guess a number from "millions" is doctrine, and a
  better answer than refusal is still owed.
- **Capability-verb extraction** — "update the claims system of record"
  implies an integration no regex can count; the LLM reader proposes facts
  today, and component hints are its natural next job.
- **The honest gaps list lives in the tool**: `fde kb gaps` and
  `fde kb sweep` report what the corpus is missing and which profile shapes
  no approach can serve yet.

## Learn more

- [ARCHITECTURE.md](ARCHITECTURE.md) — module map, the data/mechanism boundary, how to extend the registry
- [CHANGELOG.md](CHANGELOG.md) — what exists and how it was hardened
- [examples/invoice-extraction](examples/invoice-extraction/) — a full engagement transcript
- [SECURITY.md](SECURITY.md) — reporting, and what counts as security-grade here
- [llms.txt](llms.txt) — the project summarised for AI assistants

## License

[Apache 2.0](LICENSE) — chosen for the explicit patent grant, because
enterprise legal review is a real gate for the audience this is for.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: contributions enter
against a contract, and **client material never enters this repository** — only
patterns re-expressed in the framework's own words. Sanitisation is enforced in
CI: allowed paths only, history checked, credential and personal-data patterns,
and no unreviewed case can be committed.
