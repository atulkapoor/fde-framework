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
 prose        │            prunes as            six      simplest      joins       code,
 documents    │            facts arrive         gates,   applicable    decisions   evals,
 samples      │                                 one      approach,     to graph,   deploy,
 interview    └── provenance decides,           hard     cites         topology,   ops,
 hardware         never arrival order                    evidence      licences    RISKS.md
 scan                                                                     │
                                                                          v
                                              retro <── observe <── build ──> predictions
                                              case capture, override & trigger history
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
| `gates.py` | Six gates before building; one hard, five waivable with reasons |
| `decide.py` | Simplest applicable approach per component, evidence cited, rejections named |
| `decompose.py` | Which components a profile puts in scope |
| `architect.py` | The join: decisions + graph + topology + realizations + licences |
| `workflow.py` | The workflow graph; sensitivity from registry `boundary_when` |
| `moves.py` | The four moves: gates before mutation, critics before irreversibility, boundary pinning, restraint |
| `realization.py` | Pattern → stack → template resolution; copyleft classification |
| `emit.py` | Writes the project; validates everything before writing anything |
| `deploy.py` | Substrate + provisioner assets, TEARDOWN for both |
| `ops.py` | Runbook, SLOs, rollback, CI workflow |
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
| `dimensions/` | One axis of the problem: type, values, prunes, weight, recognised phrasings, who to ask |
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
| `app/` | Components (implementations or honest scaffolds), pipeline in topological order, fail-closed approval gates and critics, boundary check imported by the pipeline |
| `evals/` | Golden/edge/adversarial sets from the client's own pairs, a harness CI can gate on |
| `deploy/` | Assets for the chosen substrate and provisioner, TEARDOWN.md covering both |
| `ops/` | Runbook keyed to the failure taxonomy, SLOs from stated budgets, rollback |
| `ARCHITECTURE.md` | Decisions, rejected alternatives, undecided and unrealizable components |
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
