<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/atulkapoor/fde-framework/main/assets/banner-dark.png">
  <img src="https://raw.githubusercontent.com/atulkapoor/fde-framework/main/assets/banner-light.png" alt="fde — a framework for Forward Deployed Engineers" width="760">
</picture>

# fde — the decision before the AI build

*Evidence in, an architecture with receipts out, and a refusal when the
evidence is not there. Built for Forward Deployed Engineers; useful to
anyone who has to decide whether an AI system should exist.*

[![PyPI](https://img.shields.io/pypi/v/fde-framework?color=3775A9&logo=pypi&logoColor=white)](https://pypi.org/project/fde-framework/)
[![CI](https://github.com/atulkapoor/fde-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/atulkapoor/fde-framework/actions/workflows/ci.yml)
![Python](https://img.shields.io/pypi/pyversions/fde-framework?logo=python&logoColor=white)
[![Downloads](https://img.shields.io/pypi/dm/fde-framework?color=blueviolet)](https://pypistats.org/packages/fde-framework)
![Status](https://img.shields.io/badge/status-alpha-orange)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](https://github.com/atulkapoor/fde-framework/blob/main/LICENSE)

<p>
  <a href="#install">Install</a> ·
  <a href="#try-it">Quickstart</a> ·
  <a href="https://github.com/atulkapoor/fde-framework/blob/main/ARCHITECTURE.md">Architecture</a> ·
  <a href="https://github.com/atulkapoor/fde-framework/tree/main/examples/invoice-extraction">Worked example</a> ·
  <a href="https://github.com/atulkapoor/fde-framework/blob/main/CONTRIBUTING.md">Contributing</a> ·
  <a href="https://pypi.org/project/fde-framework/">PyPI</a> ·
  <a href="https://atulkapoor.github.io/fde-framework/">Website</a>
</p>

**fde** is an open-source framework for Forward Deployed Engineers: it takes a
client engagement from a problem statement to a runnable, deployable AI
project — with every decision traced to a fact, and every fact traced to a
source.

Not an agent framework — the thing that decides whether you need one, picks
it as a stack when you do, and grades what it builds.

Forward deployed engineers arrive with incomplete information, a client who may
not know what they need, and a deadline. This is the tooling for that:
structured discovery and requirements intake, a decision engine that cites its
evidence, and code generation that ends in something you can actually deploy —
including on-premise, inside a customer VPC, or fully air-gapped.

```bash
pip install fde-framework
fde start acme --statement "Extract fields from supplier invoices."
fde ask acme --role admin        # role-scoped discovery interview
fde architect acme               # topology + chosen approaches (rationale lands in ARCHITECTURE.md)
fde report acme                  # the decision brief, for whoever has to act on it and is not here
fde build acme --out project     # refuses: eight gates guard the build
# ...verify data access, capture the baseline, name the eval owner (each gate prints its remedy), then:
fde build acme --out project     # code + evals + deploy assets + runbook
```

<img src="https://raw.githubusercontent.com/atulkapoor/fde-framework/main/assets/demo.png" alt="fde in a terminal: a paragraph becomes typed facts, an architecture with a fingerprint, and a build that refuses until the hard gate passes" width="780">

*That refusal at the end is the product working: no baseline, no verified data
access — no build. The remedies ship with every gate.*

## In thirty seconds

You give it the problem as the client put it, the client's own examples,
the constraints, a baseline someone measured, and where it has to run.
It gives back an architecture decision with its receipts, an exam the
build has to pass, an implementation driven inside a fence, a deployment
package, a scorecard of what the build can prove, and a record of what
was never settled. It refuses to build until the evidence is there, and
it can say stop.

```bash
pip install fde-framework
fde doctor               # the interpreter, the package, the registry, the extras: measured, not guessed
fde start acme --statement "Route each support message to one of 77 queues."
fde next acme            # the one thing to learn or do next, and what turns on it
```

One minute, nothing to bring: paste two problems and see which one is
decidable yet. For what the whole loop looks like on a real dataset,
including the one time the framework told itself to stop, read the
[banking run](https://github.com/atulkapoor/fde-demo-banking#the-operating-loop-closed).

```
$ fde triage --statement "Route each inbound support message to one of 77 queues; customer data may not leave our cloud account." \
             --statement "Answer staff questions from 400 policy PDFs inside the firewall."
ranked by what the statement already settles:

  1. Route each inbound support message to one of 77 queues; customer...
     1 fact(s) read, 9% of what gets decided settled, 8 component(s) in scope
  2. Answer staff questions from 400 policy PDFs inside the firewall.
     1 fact(s) read, 6% of what gets decided settled, 5 component(s) in scope

This ranks decidability, not value: the business case comes from the baseline,
and the baseline comes after `fde start`. A candidate ranked low is
under-described, not unworthy.
```

**It's working if**, in your own run, you see these and not their opposites:

- the first thing it names is not a model: a connection that returned
  real rows, a baseline someone measured, a person who owns the number;
- a build is refused, the remedy printed beside the gate, and nothing is
  written where the build would have gone;
- every number on a card says which exam it came from, and whether that
  exam was in-sample;
- the record says *stop* on a condition someone wrote down beforehand,
  and the stage says so until a person answers it;
- the brief a stranger reads says what the terminal said, in the same
  words.

**Inside your coding agent.** The same commands are an MCP server, so an
engineer in Claude Code or Cursor can ask what to learn before building
without leaving the editor:

```bash
pip install "fde-framework[mcp]"
fde mcp --check                      # what it would serve, and from where, without serving
claude mcp add fde -- fde mcp        # Claude Code
```

The tools say what the agent *can* do; a skill says *when*. The `fde`
skill tells a coding agent that, before it scaffolds an AI system, it
triages what the statement settles, opens the engagement and asks for
the next thing to learn -- and that building, waiving and attesting are
yours, at your terminal. One line, for the agents that take skills:

```bash
/plugin install fde --marketplace atulkapoor/fde-framework   # Claude Code 2.1.275+
npx skills@latest add atulkapoor/fde-framework              # Cursor, Codex, Copilot, Gemini and the rest
```

The skill is [`skills/fde/SKILL.md`](https://github.com/atulkapoor/fde-framework/blob/main/skills/fde/SKILL.md),
readable before you install it; it uses the MCP tools when they are
configured and the command line when not.

For Cursor or any other stdio client, the server is the command `fde` with
the argument `mcp`:

```json
{ "mcpServers": { "fde": { "command": "fde", "args": ["mcp"],
                           "env": { "FDE_WORKSPACE": "/path/to/your/engagements" } } } }
```

It serves `triage`, `start`, `frame`, `status`, `next`, `stage`, `debt`,
`stop_when` and `history`, each returning exactly what the terminal prints,
refusals included, beside a small envelope an agent can branch on without
parsing prose: `schema_version`, `status` (ok, blocked, refused, failed),
`mutated`, and the workspace. The status follows the command's exit,
never a reading of its text; `mutated` is measured, the record's files
hashed before and after, so a write that failed partway and left changes
says so. Its contract is a JSON Schema, `fde mcp --schema`, that every
reply is tested against; a client pins `schema_version`, which moves
when a field changes meaning or goes away, and the schema admits fields
it does not name, so a field added keeps a client's copy valid. It moved
to 2 when `mutated` became a measurement and to 3 when `text` became
required -- added under a closed 2 at first, which a strict client would
have rejected; an outside reading caught it. An engagement is named as `start` named
it (`start(name="acme")`, then `status(engagement="acme")`), or by its
path. An agent is not a person, so every path it supplies must stay
inside one workspace, the directory the server started in or
`FDE_WORKSPACE`; a path outside it, a traversal, or a symlink that points
out is refused in words, and engagement names are plain names. The two
tools that write to the record, `start` and `frame`, say so and carry the
protocol's hints so a client can ask first. Calls run one at a time
inside the server, so an agent that asks for `status` and `next` in the
same breath gets both. Exercised against two real clients: the official
MCP Python client over stdio, in the test suite, with concurrent calls,
an abandoned call and a record changed on disk between calls; and Claude
Code 2.1, by hand, from the configuration above. Building, implementing
and deploying are not served; they stay on the command line, where the
person who runs them is accountable for them.

> ### Five founding engagements
> One real workflow, your real examples, a measured baseline, and someone
> who owns the number. You get a written answer -- build it, change the
> design, or don't -- with the receipts, and the system where the evidence
> earns one. Your data stays in your environment. **No fee for the first
> five.** [How it goes](https://atulkapoor.github.io/fde-framework/engage.html)
> · [Bring a workflow](https://github.com/atulkapoor/fde-framework/issues/new?template=engagement.yml)

## What it does

| | |
|---|---|
| **Discovery that compounds** | Prose, PDFs, sample pairs, a role-scoped interview and a hardware scan all feed one profile — provenance decides conflicts, never arrival order, and disagreement between people is surfaced as a finding |
| **Gates before building** | Eight checks with remedies; verified data access cannot be waived, and every waiver ships in the project's `RISKS.md` with its reason |
| **Decisions with receipts** | Simplest applicable approach per component, cited evidence, named rejected alternatives — and `fde override` records your call and honours it on every later run |
| **A real project out** | Pipeline in topological order — multi-modal inputs fan out one perception path per modality — fail-closed approval gates and critics, an eval harness CI can gate on — recall@K for the retrieval layer alone where one exists — deploy assets for the substrate that was actually earned, a runbook with a diagnosis walk, SLOs carrying the captured baseline, teardown A decision read off labelled text ships a fitted classifier that must beat the majority; a fine-tuning decision ships its data path -- recorded split, LoRA recipe, before/after on the holdout. |
| **Deterministic by design** | The decision path never calls an LLM: same profile, byte-identical project — a diff between builds means a decision changed. Model assistance exists only as opt-in commands, and the boundary doctrine governs them |
| **Jurisdiction as data** | Locale packs preset answers at the weakest provenance and attach dated compliance obligations to the build; they can never change how decisions are made |
| **Self-evolution, honestly** | Overrides, trigger calibration and anonymised cases are captured per engagement; the corpus grows only through human-reviewed ingestion |
| **An engagement, not a build** | The stage -- discovery, validation, prototype, pilot, production, adoption, retrospective -- is computed off the record, never declared. A drift check reads the deployed service's journal against the exam and opens an incident that pulls production back to pilot; a value estimate puts the measured system in the client's own figures, every line labelled measured, stated, assumed or derived |


## How it fits together

<img src="https://raw.githubusercontent.com/atulkapoor/fde-framework/main/assets/how-it-fits.png" alt="statement to typed facts to answer space to the gates, then decide, architect, emit, implement — registry as data, deterministic builds" width="800">

Discovery narrows an answer space; gates decide whether building is honest
yet; the decision engine picks the simplest applicable approach per component
and cites why; emit writes a project whose exam fails until it is truly
implemented. The full design is in [ARCHITECTURE.md](https://github.com/atulkapoor/fde-framework/blob/main/ARCHITECTURE.md).

---

## Bring an engagement

The claim ladder below ends on a rung only engagements can move. The first
five that run to the protocol are free, your data never leaves your
environment, and a stop is a legitimate outcome.
[`ENGAGE.md`](https://github.com/atulkapoor/fde-framework/blob/main/ENGAGE.md)
says what each side gives and gets, with the agreement in plain language;
an [engagement proposal](https://github.com/atulkapoor/fde-framework/issues/new?template=engagement.yml)
is the front door, and `fde triage --statement "..."` is the first step you
can run yourself.

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

## Status: built, demonstrated, unproven

Three different claims, and the differences are the point. Read as a
ladder, so nothing here can be over-read:

| Claim | Status | The evidence, and where it stops |
|---|---|---|
| The framework is implemented | verified | 1,352 tests on three Pythons in CI; lint clean; every audit finding pinned as a check before it was fixed; every release installed from the published wheel into a fresh interpreter and walked through the first five minutes |
| A build is reproducible | verified | byte-identical rebuild pinned by test; each public demo carries a Reproduce section and its digests |
| The decisions generalise | partial | four shapes (extraction, freeform QA, a labelled decision, seventy-seven-way routing) on real data; one industry set; `fde kb sweep` names the shapes nothing serves |
| The deliverable is production-reliable | unverified | no production engagement; the banking operating loop ran on a laptop and its record says so |
| A business outcome moved | unverified | every VALUE.md rests on stated figures; no outcome has been recorded on any engagement |
| An FDE is faster or righter with it | unverified | no comparison against an engineer working without it |
| The framework improves decision quality over an expert without it | unverified | the central thesis; nothing on any record measures it yet. [`EXPERIMENT.md`](https://github.com/atulkapoor/fde-framework/blob/main/EXPERIMENT.md) is the protocol the first engagements will run to |

**Demonstrated**: four complete engagements have run end to end on real
data, all public with every refusal preserved.

- [fde-demo-receipts](https://github.com/atulkapoor/fde-demo-receipts) --
  626 scanned receipts: the holdout refused an overfit implementation, and
  a measured plateau flipped the design from rules to a model, reason on
  the record.
- [fde-demo-complaints](https://github.com/atulkapoor/fde-demo-complaints) --
  2,034 real consumer complaints through the decision shape: the exam
  refused ambiguous ground truth before it existed, and the loop finished
  **green with the holdout passing**, the framework's first.
- [fde-demo-rfc-qa](https://github.com/atulkapoor/fde-demo-rfc-qa) --
  freeform QA over 58 real RFCs: 100% recall@10 on real queries, then the
  calibration gate **refusing its own judge** exactly as the prediction
  published beforehand said it would (73.7% agreement, refused; the
  judge's 89.5% was 26 points of flattery over the hand-graded 63.2%).
- [fde-demo-banking](https://github.com/atulkapoor/fde-demo-banking) --
  an industry use case: support intent routing for a retail bank over
  13,083 real messages and seventy-seven queues. The finished deliverable
  is an assist-mode router that abstains and says why, at 90.2% on what
  it routes with 18% handed to a person, scored on a 3,036-case holdout
  and the vendor's own test split.

Outside readings have shaped every release since, each finding pinned as
a check before it was fixed; the story, pass by pass, is in
[`HISTORY.md`](https://github.com/atulkapoor/fde-framework/blob/main/HISTORY.md),
which is the one place that counts them.

**Built**: the pipeline exists end to end — intake (prose, documents, sample
pairs, role-scoped interview, hardware scan) → fact log with provenance →
permutation space → eight gates → decide → architect → build (code, evals,
deploy and ops assets, `RISKS.md`, `COMPLIANCE.md`) → retro and case
capture. Overrides are honoured on the next run, trigger observations feed
calibration, and a reviewed case can enter the corpus. The test count is
stated once, in the claim ladder above, and updated at every release;
eleven fresh-eyes audit passes, every finding resolved and the fix pinned
as a regression test; CI gates on the suite, lint, and a sanitisation scan of
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

**Side by side.** [`BENCH.md`](https://github.com/atulkapoor/fde-framework/blob/main/BENCH.md)
reads the same figures off all four records with `fde bench`: stage, the
out-of-sample rows on each card, the gap, incidents. The banking run is the
one where the whole operating loop has run in public -- two field streams
through the delivered build, a drift incident opened and closed on the
record, a value document -- and its
[README](https://github.com/atulkapoor/fde-demo-banking#the-operating-loop-closed)
says what the deployment was (a laptop) and what the campaign was (a
drill).

| Engagement | Stage | Card | Holdout | On the answered | External |
|---|---|---|---|---|---|
| receipts | pilot | 17/22 | 56.7% on 30 | 56.7% | -- |
| complaints | pilot | 17/22 | 73.9% on 46 | 75.6% | -- |
| rfc-qa | prototype | 16/23 | 30.0% on 10 | 30.0% | -- |
| banking | production (a laptop, attested as such; stopped once by its own stop condition, cleared at the shipped 1.0-nat margin) | 23/25; does not beat the bank's baseline, on coverage | 73.8% on 3,036, abstaining 18.2% | 90.2% | 71.6% on 3,079 |

*Stage* is the record's lifecycle stage, computed from its evidence by
`fde stage`. `production` means the build was deployed and attested by
name and the field has been journalled through it -- here on a laptop, as
the record says -- not that production reliability is proven; the claim
ladder above keeps that unverified until a client's production says
otherwise.

## Two rules

Every intake surface — prose, interviews, scans, sample pairs, the client's
existing stack — emits facts into one profile, and two rules make that safe.
**Arrival order never decides anything** — provenance does, and it is
dimension-dependent: a measurement outranks anything said about the
environment, while a stated requirement outranks a measurement, since you
cannot detect a latency *budget*. And **two people disagreeing is a finding,
not a conflict to resolve**; the dimension is left unresolved and reported,
because the gap between what a sponsor believes and what a user experiences
is usually the most valuable thing discovery produces.

The full pipeline those rules feed — space pruning, decomposition, the seven
gates, decision, emission — is in
[ARCHITECTURE.md](https://github.com/atulkapoor/fde-framework/blob/main/ARCHITECTURE.md).

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

Prerequisites: Python 3.11+.

```bash
pip install fde-framework          # the registry ships inside the wheel
fde start acme --statement "..."   # works from any directory
```

Extras: `pip install "fde-framework[documents]"` for PDF/docx intake, `[llm]`
for the hosted-model reader path.

Or from source (contributors — a local ./framework outranks the packaged copy):

```bash
git clone https://github.com/atulkapoor/fde-framework.git
cd fde-framework
python3 --version   # must say 3.11+; an older python3 makes pip backtrack for ages instead of failing fast
python3 -m venv .venv && .venv/bin/pip install -e ".[dev,documents]"
```

Or with [uv](https://docs.astral.sh/uv/): `uv venv && uv pip install -e ".[dev,documents]"`

### Optional extras

| Extra | Installs | For |
|---|---|---|
| `documents` | pypdf, python-docx | `fde frame --file brief.pdf` — PDF and Word intake |
| `mcp` | mcp | `fde mcp` — the conversational commands served to a coding agent over stdio |
| `dev` | pytest, ruff, mcp | running the test suite and linter |

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
fde start acme --statement "Extract fields from supplier invoices."
fde ask acme --role admin        # bare names resolve to ./engagements/acme
fde status acme                  # gates, gaps, disagreements
fde architect acme               # the design, with rationale
fde build acme --out project     # refuses until gates clear

fde scan acme                    # what this hardware runs
fde cost --requests-per-day 500000 --model-b 70   # dated fleet sizing

fde kb validate   # parse and cross-link the registry
fde kb gaps                        # what the corpus is missing
fde kb sweep                       # profiles no approach can serve
```

`kb validate` is strict, because CI runs it and a warning nobody reads is not a
check. `--lenient` exists for the hour when you are mid-way through authoring
content and the links do not resolve yet.

A complete worked engagement — real transcript, synthetic client — lives in
[examples/invoice-extraction](https://github.com/atulkapoor/fde-framework/tree/main/examples/invoice-extraction).

## What a build emits

```
project/
├── app/                  # components, pipeline, controls, boundary check
│   ├── components/       #   implementations or honest scaffolds — never silent gaps
│   ├── pipeline.py       #   topological order; approval gates before anything mutative
│   ├── controls.py       #   fail-closed gates & critics — when anything mutative was decided
│   ├── boundary.py       #   imported at startup when data may not leave
│   ├── contract.py       #   RefusedInput: forbidden input is refused, never guessed at
│   └── llm.py            #   the one model touchpoint — when a decision needs a model (boundary-gated)
├── evals/                # golden / edge / adversarial sets from the client's own pairs
│   ├── harness.py        #   fails CI until implemented; judge-based when the evaluation decided judged
│   ├── retrieval.py      #   recall@10/50, the first relevant hit's rank, and how much of it the reasoning step shows — when retrieval answers ranked queries
│   ├── acceptance.md     #   blind UAT protocol for the client's own judges, with the exam record
│   ├── manifest.json     #   split seed, holdout share, SHA-256 of every eval file and the holdout
│   └── load.py           #   p95 against the stated budget (when one was stated)
│   ├── shapes.py         #   the one envelope every step reads and writes; refusals at the door
│   ├── service.py        #   the HTTP edge: identity, request ids, framing, readiness, drain
│   └── ledger.py         #   append-only audit + idempotency keys under STATE_DIR — when anything is outward
├── tests/                # the deliverable's own model-free smoke: contract, fence, empty-exam refusal
├── train/                # when fine-tuning was decided: recorded split, LoRA recipe, before/after on the holdout
├── deploy/               # the substrate that was earned, its full install path, + TEARDOWN.md for all of it
├── ops/                  # runbook (first-five-minutes commands up top), diagnosis walk, SLOs, rollback
├── ARCHITECTURE.md       # scope read-out, decisions, tools & alternatives, agent posture
├── RISKS.md              # every waived gate and overridden recommendation
└── COMPLIANCE.md         # jurisdiction obligations, when a locale pack was applied
```

Emitted quality is a pinned property, not a promise: the framework's own
test suite emits projects across representative architecture shapes and
holds every emission to the operational contract, from every environment
variable the code reads being documented to a classifier that refuses to
serve a constant; the full list of what is held, and the audit passes that
put each check there, is in
[`HISTORY.md`](https://github.com/atulkapoor/fde-framework/blob/main/HISTORY.md).
A quality finding lands there as a check before
it lands anywhere as a fix ([`tests/test_acceptance.py`](tests/test_acceptance.py),
[`tests/test_finetune.py`](tests/test_finetune.py)). And the claim is
measurable per build: `fde scorecard <project> --holdout <file> --external
<file>` runs what the deliverable can prove about itself and writes
`SCORECARD.md` with a verdict that is a count of rows, never an adjective,
and says which rows measure fitness and which measure self-consistency.

## After the build: the engagement's operating loop

`fde build` used to be where the framework stopped. An engagement does not
stop there, so the record now carries the rest of it, and every part of it
is either computed from evidence or attested by a named person -- never
declared by the tool.

- **`fde stage`** computes where the engagement stands. Each stage is a set
  of criteria the record shows or does not: a statement; gates passing or
  waived, pairs seeded, a holdout drawn, data access attested; a build with
  its exam; a scorecard whose out-of-sample rows hold and whose edge answered
  a valid request; a deployment on record with no open incident; an adoption
  figure measured in the field; a retrospective captured as a case. Every
  transition is appended to `lifecycle.jsonl` with its evidence, so
  time-to-pilot and every reversal can be read back.
- **`fde drift`** reads the deployed service's journal -- the same `answered`
  lines the emitted service writes -- and compares abstention, decision mix,
  errors and margins against the exam and the last scorecard. Past a
  threshold it opens an incident on the record and exits 1. An open incident
  pulls production back to pilot; `fde incident close` needs a note saying
  what was done.
- **`fde value`** writes `VALUE.md`: the automated share and its accuracy from
  the holdout row, hours and money from the recorded baseline, build and run
  costs from the caller, payback, and a Wilson interval on the accuracy.
  Every line says what it rests on, so the number is argued row by row.
- **`fde deployed`** and **`fde outcome`** are attestations: where it runs,
  who put it there and which build it is (`--project`, which every command
  that reads a project by default then reads); adoption, time to first
  value, whatever the client measured. **`fde outcomes`** prints what the record shows without anyone's
  opinion -- transitions, days to pilot, loop rounds, reversals, incidents.
- **`fde stakeholders`** maps the engagement's people as the record shows
  them: which of the five roles has been heard (every session carries the
  role and, when given, the name), who signed what (`--by` on data-access,
  security-review, waive, deployed, outcome and incident close), which roles
  were never asked, and what is on the record with nobody's name on it.
  `fde stakeholder add` names the people who have not spoken yet. It is a
  map, not a contact list.
- **`fde import`** turns a client export -- `.csv`, `.tsv`, `.jsonl`, `.json`,
  with the client's column names -- into the pairs the intake reads, and
  reports what it kept, skipped for an empty side, dropped as a duplicate,
  and counts as verified. Nothing is verified unless the caller says which
  column and value means a person checked it.
- **`fde bench`** reads the same figures off every engagement record, side
  by side: stage, the out-of-sample rows on its card, the gap, incidents,
  days to pilot. [`BENCH.md`](https://github.com/atulkapoor/fde-framework/blob/main/BENCH.md)
  is the four public demos, computed this way.
- **`fde history`** prints every dated entry on the record in order, the
  undated ones above it, one line each -- the page to read when picking an
  engagement up.
- **`fde outcome-contract`** is the eighth gate: owner, metric, its value
  today, its target, how it is measured and over what window. Nobody builds
  until somebody has agreed which number the system exists to move, or
  waived that with a reason that ships in RISKS.md. The adoption stage then
  reads the contracted metric back from what was measured in the field.
- **`fde debt`** is the decision debt: everything the engagement rests on
  that nobody has settled -- a gate still failing, a waiver standing in for
  a condition, a fact the framework guessed or a person merely said where a
  measurement was possible, two people disagreeing, an attestation with no
  name on it, a role never asked, an incident open, a component nothing
  serves -- each with an owner, what blocks on it, and its age.
- **`fde next`** now says what hangs on the question it asks: the evidence
  already on record for that dimension, every candidate answer tried, and
  the decisions that turn on it -- so the question is asked knowing why.
- **`fde predict`** records what the engagement expects before it measures
  -- `holdout_accuracy >= 0.82`, `field_abstain_rate <= 0.22` -- in the
  stop-condition grammar, with a confidence if the forecaster has one, and
  what was in hand when it was made: which figures the record had already
  measured, and digests of the card and the profile. A forecast about a
  figure already measured is kept and marked, per figure, because a
  forecast made after the number is not a forecast. After the score each
  is held, missed or not measured, with the signed error; once five or more
  carry a confidence, the held rate is set beside the mean confidence.
- **`fde implement --sandbox docker`** runs the coding agent in a container
  closed by construction: only the project mounted, root read-only with a
  scratch `/tmp`, every capability dropped and none gainable, your own user
  rather than root, bounded memory, CPU and processes, the environment a
  default allowlist, and no network unless someone with a name and a
  reason opened it at the terminal (`--allow-network "who: why"`,
  `--env-allow NAME`). The emitted `ops/agent-policy.yaml` sits inside
  the directory the agent writes to, so it can only narrow: it names the
  image and bounded limits, and anything wider it asks for is a request
  the log shows ungranted. The file is part of the fence -- an agent that
  rewrites it, or plants one, has the change reverted and the round says
  so. The implementation log records the image digest the agent actually
  ran on; without the sandbox it says the agent had the host.
- **`fde experiment`** runs the protocol in
  [`EXPERIMENT.md`](https://github.com/atulkapoor/fde-framework/blob/main/EXPERIMENT.md)
  on the record: `start` assigns the arm by a seeded draw balanced within
  the shape, records the engineer, the order and a difficulty vector read
  off the profile, and freezes the forecasts, the contract and the stop
  conditions before the build; `close` reads the measures off the record,
  or off the control arm's log kept in the template it writes, and lists
  what is missing; `packet` renders the blind review in one plain form for
  both arms; `review` records the reviewer's fixed form and their guess at
  the arm; `withdraw` records an engagement leaving with the arm it drew, so the
  report can count withdrawals by arm; `report` pairs within shape by the
  nearest frozen difficulty and prints the distance, sets the primary
  endpoint beside the secondaries and beside a floor line for any score
  under three, breaks the figures out by engineer and by half of the
  series, gives the blinding accuracy per packet version, and names the
  rung of evidence the count has reached.
- **`fde stop-when`** records what evidence would stop the engagement --
  `answered_accuracy < 0.88`, `abstain_rate > 0.25`, `adoption < 0.4` --
  over figures the record measures: the scorecard's out-of-sample rows, the
  field journal, the outcomes recorded in the field. A triggered condition
  makes STOP the engagement's stage, on the record with the trigger and the
  threshold, until the condition is restated with a reason, the build is
  changed and scored again, or the case is captured. A figure the record
  has not measured leaves its condition unjudged and says so.

What this still is not: a live connector to a ticketing or data system
(an export is the interface, and the only one testable without a client's
credentials); a benchmark corpus (four public demos are four rows, and the
bench says so); collaboration beyond a git-native record with names on it.
Each waits for engagements that have not happened yet.

## The full lifecycle, copy-paste

Everything below runs from an empty directory after `pip install fde-framework`:

```bash
fde start acme --statement "Extract fields from scanned supplier invoices; \
data cannot leave; 200,000 documents, 8,000 verified; a person is waiting."
# plays back the typed facts it read, and the three questions worth asking next

fde ask acme --role eval_owner       # answer what discovery still needs
fde status acme                      # facts by scope, gates, % settled

cat > baseline.yaml <<'YAML'
volume: {value: 20000, unit: docs/month, definition: invoices received by AP}
cycle_time_per_unit_seconds: {value: 300, unit: s, definition: arrival to posted}
labour_hours_per_week: {value: 35, unit: h/week, definition: AP team keying time}
rework_rate: {value: 0.1, unit: ratio, definition: entries corrected after post}
exception_rate: {value: 0.07, unit: ratio, definition: routed to a human queue}
error_rate: {value: 0.04, unit: ratio, definition: wrong amount or vendor posted}
business_metric: {value: 9, unit: days, definition: mean days payable outstanding}
sampled: {n: 40, method: random invoices across two months}
YAML
fde baseline acme --file baseline.yaml
fde data-access acme --note "read replica returned 14 real rows"
fde security-review acme --note "client infosec walked the data paths"
fde ask acme --role eval_owner       # or: fde waive acme client_readiness --reason "..."

fde build acme --out project         # refuses until the gates truly pass
python project/evals/harness.py      # red: empty until pairs are seeded, then red until implemented -- that's the exam
fde implement project                # drive a coding agent until it's green
fde scorecard project --holdout engagements/acme/artifacts/holdout.jsonl   # measure it

fde stage acme --project project     # where it stands, computed off the record
fde deployed acme --note "runs in the client VPC; platform team put it there" --project project
fde drift acme --journal service.log --project project   # the field against the exam
fde incident acme close inc-001 --note "holdout re-scored; pairs redrawn"
fde outcome acme --metric adoption=0.62 --note "support lead's dashboard, week 3"
fde value acme --project project --hourly-cost 40        # VALUE.md, line by line
```

## Python API

The CLI is a thin layer; everything is importable. The registry loads from the
installed wheel, so this runs anywhere:

```python
from fde.architect import architect
from fde.intake.prose import parse_prose
from fde.models.profile import Profile
from fde.registry import default_root, load_registry

registry = load_registry(default_root())

profile = Profile()
profile.ingest(parse_prose(
    "500,000 scanned invoices; data cannot leave; 10,000 verified; "
    "a person is waiting; structured records out.", registry))

design = architect(profile, registry)
print(design.topology)                    # customer-vpc
for component, decision in sorted(design.decisions.items()):
    if decision.approach:
        print(component, decision.approach, decision.rationale)
```

Every decision object carries its rationale and its rejected alternatives —
the same receipts the emitted `ARCHITECTURE.md` prints.

## Common commands

| | |
|---|---|
| `fde start <name> --statement "..."` | begin an engagement |
| `fde frame <eng> --file brief.pdf` | prose or documents → facts, played back for correction |
| `fde frame <eng> --reader llm --endpoint http://localhost:11434` | a local model proposes what the deterministic reader missed, at weakest provenance |
| `fde samples <eng> --file pairs.jsonl` | input/output pairs → contract, metrics, golden/edge/adversarial evals (`--sensitive <field>` marks fields for masking) |
| `fde ask <eng> --role admin` | role-scoped interview, ordered by what changes the design |
| `fde ask <eng> --role admin --scope non_functional` | one scope axis at a time — the dedicated NFR pass |
| `fde scan <eng>` | measure the hardware, and get a local-model plan sized to it (runtime, judge, coder) |
| `fde next <eng>` | The single best next action, judged from everything recorded — ask it any time |
| `fde status <eng>` | gates, gaps, waivers, disagreements |
| `fde baseline / data-access / security-review / waive / restate` | satisfy or knowingly waive a gate |
| `fde cost --price-per-seat 25 --workflows-per-day 8` | unit economics with the levers priced; `--requests-per-day N --model-b B` for dated fleet sizing |
| `fde kb suggest --file brief.md --endpoint http://localhost:11434` | mine a brief for recogniser gaps — proposed, never applied |
| `fde kb export-training <eng> --out train.jsonl` | (brief, facts) pairs — the fine-tune flywheel, kept with the engagement |
| `fde reuse <eng> <stack>` | record what the client already operates, so reuse can beat adoption |
| `fde locale <eng> eu-gdpr` | jurisdiction pack: presets plus obligations emitted as COMPLIANCE.md |
| `fde architect <eng>` | the design, rationale and rejections |
| `fde report <eng> [--out brief.md]` | the decision brief: five statuses at a glance (decided, built, implemented, evaluated, outcome), the problem as stated, the stage, what is known and who said it, the outcome contract, the design with its reasons and rejections, what it rests on, the debt, the stop conditions, the next decision -- one Markdown file, before any build |
| `fde build <eng> --out project` | emit; refuses while gates block |
| `fde implement project/` | drive a coding agent until the emitted evals pass, inside guardrails |
| `fde scorecard project/ --holdout <file>` | measure production grade: every property the deliverable can prove, with the number, in `SCORECARD.md` |
| `fde scorecard project/ --holdout <file> --coverage-floor 0.97 --max-gap 0.08` | the engagement's own bars: the share the system must answer for the baseline row to hold (default: 1 minus the baseline's exception rate), and its limit on the golden-to-holdout gap (protocol default 20%) |
| `fde stage <eng>` | where the engagement stands, computed from the record; transitions appended to `lifecycle.jsonl` (`--no-record` to look without appending) |
| `fde deployed <eng> --note "..." [--project <dir>]` | attest the deployment: where it runs, who put it there, which build |
| `fde drift <eng> --journal <log>` | the field against the exam: abstention, mix, errors, margins; opens an incident and exits 1 when it moved |
| `fde incident <eng> list \| close <id> --note "..."` | incidents on the record; an open one holds the stage at pilot |
| `fde outcome <eng> --metric adoption=0.62` / `fde outcomes <eng>` | outcomes measured in the field; what the record shows without opinion |
| `fde value <eng> --hourly-cost 40` | `VALUE.md`: the measured system in the client's figures, every line measured, stated, assumed or derived |
| `fde stakeholders <eng>` / `fde stakeholder <eng> add --name --role --stake` | who has been heard, who signed what, which roles were never asked |
| `fde import <eng> --file tickets.csv --input body --output queue --verified-when checked=yes` | a client export into pairs, with a report; then `fde samples` |
| `fde bench <eng>=<project> ...` | the same figures off every record, side by side, in `BENCH.md` |
| `fde history <eng>` | every dated entry on the record in order, one line each |
| `fde mcp` / `fde mcp --check` | serve triage, start, frame, status, next, stage, debt, stop-when and history to a coding agent over stdio, confined to `FDE_WORKSPACE`; `--check` lists what it serves |
| `fde doctor` | whether this install can do what the README says: interpreter, package, registry, working directory, extras, docker, the agent, the linter; exit 1 only on what the core needs |
| `fde outcome-contract <eng> --owner --metric --baseline --unit --target --method --window` | the eighth gate: which number this system exists to move, from what to what, measured how, by when |
| `fde debt <eng>` | decision debt: what nobody has settled, with an owner, what it blocks, and its age |
| `fde stop-when <eng> --when "answered_accuracy < 0.88"` | what evidence would stop the engagement; judged against the record, exit 1 and a STOP stage when triggered |
| `fde predict <eng> --when "holdout_accuracy >= 0.82"` | a forecast before the measurement; judged after it, with the signed error |
| `fde implement project/ --sandbox docker --env-allow ANTHROPIC_API_KEY --allow-network "Priya: hosted model"` | the agent in a container closed by construction; the network only with a name and a reason, both in the log |
| `fde predict <eng> --when "holdout_accuracy >= 0.82" --confidence 0.7` | a forecast with what was in hand; judged after the measurement, with the signed error and, at five or more, the held rate against the mean confidence |
| `fde experiment <eng> start --engineer "..."` / `close` / `packet` / `review` / `withdraw` / `fde experiment <series> report` | the experiment run by the record: arm assigned, pre-build state frozen, measures read, blind packet, reviewer's form and guess, withdrawals by arm, pairs by nearest difficulty with the floor line and the breakdowns |
| `--by "<name>"` on data-access, security-review, waive, deployed, outcome, incident close | the signer's name on the record; the stakeholder map points at entries without one |
| `fde triage --statement "..." --statement "..."` | rank candidate problems by what discovery can already decide |
| `fde override --component X --choose Y --because "..."` | your call, recorded and honoured |
| `fde observe / retro` | record trigger firings; capture the case |
| `fde kb validate / gaps / sweep` | registry health, work items, dead zones |

## Why not RAGAS or TruLens?

Deliberately. Their headline metrics are judge-scored, and an uncalibrated
judge is the failure mode this framework has now measured first-party: a
local judge inflated results by 26 points before the calibration gate
refused it ([the run is public](https://github.com/atulkapoor/fde-demo-rfc-qa)).
The emitted evals are seeded from the client's own verified examples,
stdlib-only — they run inside an air gap and hand over with zero
dependencies — reference-based with discrete verdicts, and no judged number
is quoted before the judge beats a human-agreement bar against the named
eval owner. If your team wants RAGAS or TruLens dashboards alongside, point
them at the same golden pairs — the JSONL is the same shape. The gate a
delivery is graded on stays calibrated, or stays silent.

## Troubleshooting

**`no registry here`** — you passed `--registry`/`--root` at a directory that
holds no registry. Drop the flag (the corpus ships inside the package) or
point it at the `framework/` of a source checkout.

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

Four commands are the deliberate exceptions — each opt-in, each governed by
the boundary doctrine (hosted models refused unless the engagement states
data may leave; local endpoints always allowed):

- `fde frame --reader llm` — a model proposes facts, at the weakest provenance
- `fde kb suggest` — mines a brief for recogniser gaps, proposing (never applying) vocabulary
- `fde implement` — drives a coding agent you name
- the judge-based eval harness in *generated* projects whose evaluation
  decided `judged` (`LLM_ENDPOINT`, hosted path refused inside a boundary)

Nothing calls a model silently, and `fde scan` recommends a local model
sized to your hardware so none of it needs to leave the machine.

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
- **More locale packs and stacks** — both are data; contributions enter
  against [CONTRIBUTING.md](https://github.com/atulkapoor/fde-framework/blob/main/CONTRIBUTING.md)'s contract (and the [code of conduct](https://github.com/atulkapoor/fde-framework/blob/main/CODE_OF_CONDUCT.md)).
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
The honest gaps list lives in the tool itself: `fde kb gaps` and
`fde kb sweep` report what the corpus is missing and which profile shapes
no approach can serve yet.

## Documentation

| I want to… | Read |
|---|---|
| Run the whole lifecycle once | [The full lifecycle, copy-paste](#the-full-lifecycle-copy-paste) |
| See a real transcript with expected output | [Worked example](https://github.com/atulkapoor/fde-framework/tree/main/examples/invoice-extraction) |
| Understand the moving parts | [ARCHITECTURE.md](https://github.com/atulkapoor/fde-framework/blob/main/ARCHITECTURE.md) |
| Understand a gate that just refused me | `fde status <eng>` — every gate names its remedy and its clearing command |
| See complete engagements on real data, refusals preserved | [fde-demo-receipts](https://github.com/atulkapoor/fde-demo-receipts) · [fde-demo-complaints](https://github.com/atulkapoor/fde-demo-complaints) · [fde-demo-rfc-qa](https://github.com/atulkapoor/fde-demo-rfc-qa) · [fde-demo-banking](https://github.com/atulkapoor/fde-demo-banking) |
| Pick a local model with receipts | [Local models, measured](https://atulkapoor.github.io/fde-framework/models.html) |
| Add a dimension / approach / template | [CONTRIBUTING.md](https://github.com/atulkapoor/fde-framework/blob/main/CONTRIBUTING.md) — incl. the template context table |
| Use it as a library | [Python API](#python-api) |
| Report a vulnerability | [SECURITY.md](https://github.com/atulkapoor/fde-framework/blob/main/SECURITY.md) |
| See what changed | [CHANGELOG.md](https://github.com/atulkapoor/fde-framework/blob/main/CHANGELOG.md) · [Releases](https://github.com/atulkapoor/fde-framework/releases) |


## Development

Set up as in [Install → from source](#install) (python3.11+), then:

```bash
.venv/bin/pip install -e ".[dev,documents]"
.venv/bin/pytest -q          # the full suite, about two minutes
.venv/bin/ruff check src tests
```

The registry is data: most contributions are a markdown file in `framework/`
plus a test that pins the behaviour. CI additionally runs a sanitisation sweep
over the tree and history.

## Community

Questions and engagement war stories → [Discussions](https://github.com/atulkapoor/fde-framework/discussions).
Bugs and corpus gaps → [issues](https://github.com/atulkapoor/fde-framework/issues/new/choose) (the forms ask for evidence, the way the framework does).
Conduct → [CODE_OF_CONDUCT.md](https://github.com/atulkapoor/fde-framework/blob/main/CODE_OF_CONDUCT.md).

## License

[Apache 2.0](https://github.com/atulkapoor/fde-framework/blob/main/LICENSE) — chosen for the explicit patent grant, because
enterprise legal review is a real gate for the audience this is for.

## Contributing

See [CONTRIBUTING.md](https://github.com/atulkapoor/fde-framework/blob/main/CONTRIBUTING.md). The short version: contributions enter
against a contract, and **client material never enters this repository** — only
patterns re-expressed in the framework's own words. Sanitisation is enforced in
CI: allowed paths only, history checked, credential and personal-data patterns,
and no unreviewed case can be committed. Before proposing a feature, read
[DECLINED.md](https://github.com/atulkapoor/fde-framework/blob/main/DECLINED.md):
the bar an idea has to clear, and the ones that did not, each with its
reason.
