# Architecture

How the framework is put together, and where to change what.

The one rule that explains the layout: **`framework/` is data, `src/fde/` is
mechanism.** Adding a stack, an approach, a dimension or a case is a markdown
file; editing Python means the mechanism itself was wrong. Tests enforce the
boundary, and three adversarial audit rounds have specifically hunted for
knowledge that leaked from data into code.

## The pipeline

```
intake ──> fact log ──> permutation space ──> gates ──> decide ──> architect ──> emit
 prose        │            prunes as            seven    simplest      joins       code,
 documents    │            facts arrive         gates,   applicable    decisions   evals,
 samples      │                                 one      approach,     to graph,   deploy,
 interview    └── provenance decides,           hard     cites         topology,   ops,
 hardware         never arrival order                    evidence      licences    RISKS.md
 scan                                                                     │
                                                                          v
                                              retro <── observe <── build ──> predictions
                                              case capture, override & trigger history
                                                                          │
                                                                          v
                          stage <── incident <── drift <── deployed <── scorecard <── implement
                          computed off the record; an open incident pulls production back to pilot;
                          value writes the measured system in the client's own figures
```

## `src/fde/` — the mechanism

| Module | Responsibility |
|---|---|
| `models/base.py` | Provenance ordering (dimension-dependent), `says_something` |
| `models/fact.py`, `models/profile.py` | One fact; the profile that resolves facts, keeps disagreements as findings |
| `models/schema.py` | Pydantic models for every registry kind |
| `models/respondent.py` | The five roles: sponsor, eval_owner, user, admin, skeptic |
| `intake/prose.py` | Deterministic prose → facts; refuses ambiguity rather than guessing |
| `intake/documents.py` | PDF/docx → text, refusal by name |
| `intake/samples.py` | Sample pairs → contract, metrics, golden set; settles only the shape |
| `intake/interview.py` | Role-scoped question ordering by decision divergence |
| `intake/answers.py` | One reply → a fact, or a sharpening probe |
| `factlog.py` | Append-only engagement store; sessions, statements, gate state |
| `space.py` | The permutation space; facts prune candidates to a fixed point |
| `predicate.py` | The tiny predicate grammar (`always`, `==`, `and`, comparisons) |
| `gates.py` | Seven gates before building; one hard, six waivable with reasons |
| `implement.py` | Bounded agent loop: harness as stop condition, evals/boundary/contract hashed as a fence, holdout against memorized greens |
| `intake/llm_reader.py` | Optional model-proposed facts at weakest provenance; registry-derived schema; boundary-gated |
| `decide.py` | Simplest applicable approach per component, evidence cited, rejections named |
| `decompose.py` | Which components a profile puts in scope |
| `architect.py` | The join: decisions + graph + topology + realizations + licences |
| `workflow.py` | The workflow graph; sensitivity from registry `boundary_when` |
| `moves.py` | The four moves: gates before mutation, critics before irreversibility, boundary pinning, restraint |
| `realization.py` | Pattern → stack → template resolution; copyleft classification |
| `emit.py` | Writes the project; validates everything before writing anything |
| `deploy.py` | Substrate + provisioner assets, TEARDOWN for both |
| `ops.py` | Runbook, diagnosis walk, SLOs, rollback, CI workflow |
| `training.py` | The fine-tuning data path emitted beside a finetune decision: recorded split, LoRA recipe, before/after on the holdout |
| `scorecard.py` | Production grade, measured: runs what a deliverable can prove about itself and writes SCORECARD.md with a verdict that is a count of rows |
| `lifecycle.py` | The engagement's stage, computed from the record against per-stage criteria; transitions appended with evidence; outcome metrics read off the trail |
| `drift.py` | The production loop: the service's journal read against the exam and the last card; incidents opened and closed on the record |
| `value.py` | The business-value estimate from the recorded baseline and the holdout row, every line labelled measured, stated, assumed or derived |
| `stakeholders.py` | The stakeholder map read off sessions and signatures: roles heard, names, what each signed, roles never asked |
| `importer.py` | Client exports (csv/tsv/jsonl/json) into pairs by column, with a report; nothing verified unless the caller says how |
| `bench.py` | The same figures off every engagement record, side by side, in BENCH.md |
| `history.py` | Every dated entry on the record in order, undated ones above, one line each |
| `scan.py` | Hardware detection; only a successful measurement earns DETECTED |
| `costing.py` | Dated fleet sizing; naive figure beside the real one |
| `evolution.py` | Overrides, trigger calibration, case emission |
| `registry.py` | Loads `framework/` with located errors |
| `graph.py` | Cross-link validation, gap detection, dead-zone sweep |
| `cli.py` | The user surface; every failure is a sentence, never a traceback |

## `framework/` — the knowledge

Every entry is markdown with YAML front matter (the machine's half) and a
prose rationale (the person's half — *why* the rule says what it says).

| Kind | What one entry declares |
|---|---|
| `dimensions/` | One axis of the problem: type, values, prunes, weight, scope axis, recognised phrasings, who to ask |
| `components/` | The slots a system decomposes into, and what caps what |
| `approaches/` | One way to serve components: `applies_when` / `avoid_when` predicates, complexity, evidence |
| `patterns/` | Approach × component → realizations per stack |
| `stacks/` | One tool: licence, topologies it runs in, verification date |
| `interfaces/` | The typed slots realizations claim to satisfy |
| `templates/` | Jinja2 reference implementations, one per realization |
| `cases/` | Engagement shapes anchored in the public record — the evidence approaches cite |
| `locales/` | Jurisdiction packs: presets on existing dimensions at weakest provenance, dated obligations emitted as `COMPLIANCE.md` |

### Extending it

- **New stack**: one file in `stacks/` + a realization line in the pattern +
  a template. Swapping stacks changes emitted code, never the architecture —
  a test asserts exactly that.
- **New dimension**: one file in `dimensions/` with `weight:` (or `fde kb
  gaps` reports it invisible). If a value forbids egress, declare
  `boundary_when`; if it needs a judged evaluation, `needs_judge`.
- **New approach**: predicates in front matter, rationale in prose, evidence
  or `fde kb gaps` will say nobody has done it.
- **New case**: never written by hand from a real engagement — `fde retro`
  emits it, `fde kb ingest-case` lands it as `sanitization: pending`, a human
  reviews, CI refuses pending cases.

### Named seams

Two places where code names registry content, each a single declared
constant: `graph.TOPOLOGY_DIMENSION` (which dimension is the deployment
topology) and `gates.GATE_DIMENSIONS` (dimensions the gates read). Everything
else that looks like registry knowledge in `src/` is a bug — report it.

## What a build emits

| Artifact | What it is |
|---|---|
| `app/` | Components (implementations or honest scaffolds) reading and writing one envelope (`shapes.py`), the pipeline in phase order with an ingest path where retrieval exists, fail-closed approval gates and critics, a boundary that validates every outward URL at import, the HTTP edge (`service.py`), and a durable ledger (`ledger.py`) |
| `evals/` | Golden/edge/adversarial sets from the client's own pairs, a harness CI can gate on, recall\@K of the retrieval layer where one answers ranked queries |
| `tests/` | The deliverable's own model-free smoke: the contract exists, the fence holds at import, the exam refuses to be empty |
| `deploy/` | Assets for the chosen substrate and provisioner — including the full install path the unit's demands imply — TEARDOWN.md covering both |
| `ops/` | Runbook opening with the operator's first five minutes, keyed to the failure taxonomy, a diagnosis walk (definitions first, model last), SLOs from stated budgets, the captured baseline, rollback |
| `train/` | Present beside a fine-tuning decision: a seeded, stratified, de-duplicated split with every digest recorded, the LoRA recipe that refuses changed data and names the adapter by what went into it, the before/after comparison on the holdout the split held back |
| `ARCHITECTURE.md` | Scope read-out by axis, decisions, tools and in-topology alternatives, agent posture, rejected alternatives, undecided and unrealizable components |
| `RISKS.md` | Every waived gate with its reason, every overridden recommendation |
| `COMPLIANCE.md` | The applied locale's obligations, dated, with verification notes |

## Invariants the tests defend

- Same profile → byte-identical project. A diff between builds means a
  decision changed.
- Arrival order never decides anything; provenance does.
- Only a successful measurement earns DETECTED provenance.
- No component vanishes: undecided ships as a module that raises with the
  reason.
- `emit` validates everything before writing anything.
- Client material never enters the repository (CI-enforced, history included).
- Every emission meets the operational contract: env vars documented,
  the unit's demands creatable from what ships, a model-free CI lane, a
  passing smoke on a fresh emission, lint-clean code, a payload path that
  composes and refuses garbage, a boundary that refuses outside
  endpoints, a ledger that survives restart, a service that carries a
  request id on every answer, a request contract that refuses forged
  results, retrieval and perception linear in their input, a journal that
  survives concurrency, a corpus and a ledger that survive a bad file, a
  request contract generated from the build's own request path, an index
  sized against the unit's memory cap, and edge tests inside the
  deliverable (`tests/test_acceptance.py` — a quality finding lands there
  as a check before it lands as a fix).
