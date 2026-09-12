# Changelog

Notable changes, oldest last. Format follows [Keep a Changelog](https://keepachangelog.com/);
the project is pre-release, so everything sits under 0.1.0 until the first tag.

## [Unreleased]

## [0.1.9] — 2026-09-12

Shaped by the model-in-the-loop demonstrations and a benchmark review of
small local judges:

- The emitted judge speaks a discrete rubric — correct / partial /
  incorrect mapped to {1, 0.5, 0} — instead of inventing a decimal.
  Local-scale judges agree with human graders far better on verdicts than
  on open-ended numeric scores, and the reference in the prompt is what
  makes a small judge legitimate at all.
- An agent round that outlives its budget is a round result, never a
  traceback: the receipts demonstration's local-inference rounds ran past
  the hardcoded hour and the loop died mid-sentence. `--agent-timeout`
  raises the budget when the model runs inside the eval loop, the overrun
  lands in the round log with what the agent said, and a check that
  exceeds its own budget reports rather than raises.
- Two new worked examples, each a replay-tested real transcript:
  `examples/policy-qa` (freeform + retrieval: the recall eval, the judged
  evaluation and its offline-evaluability waiver, an honestly undecided
  component) and `examples/support-triage` (decisions that act: the
  governed tool boundary, critics, idempotency — and model-planner
  rejected on the record as not-simplest).
- `fde next` asks only while an answer could change what gets built, and
  names the undecided components; the prose reader survives hard-wrapped
  briefs; "Decide each …" reads as a decision workload; the next-move
  footer fails silently instead of leaking a registry error.

- `fde next`'s ask rung now asks only while an answer could change what
  gets built: an honestly unmeasured dimension (the flagship unmeasured-
  coverage case) no longer traps the ladder on a question nobody can
  answer while every component already decides without it. When it does
  ask, it names the undecided components the answer would unblock.
- "Decide each …" reads as a decision workload — both demonstration
  engagements' own statements parsed to nothing and leaned on samples
  inference for the shape they declared.

- Two new worked examples, each a replay-tested real transcript:
  `examples/policy-qa` (freeform answers over 40k documents — the retrieval
  recall eval, the judged evaluation and its offline-evaluability waiver
  inside a boundary, and an honestly undecided component) and
  `examples/support-triage` (decisions that act through three systems —
  the governed tool boundary, approval gates, critics, idempotency, and
  model-planner rejected on the record as not-simplest).
- The prose reader treats a single newline as the space it is: briefs
  arrive hard-wrapped, and "data cannot leave" split across a line break
  silently vanished. A blank line stays a paragraph boundary.
- The next-move footer loads the registry quietly; its failure is silence,
  never a leaked error line.

## [0.1.8] — 2026-09-11

The helping-hand release, shaped by walking the demonstration engagement
as a user who only did what the tool said next:

- `fde next <engagement>`: the single best next action, judged from
  everything recorded — gates first (with the clearing command), then the
  exam, the highest-value open question, the build, the implement loop.
  The gates' remedy pattern, generalized to the whole lifecycle. Every
  recording command (ask, samples, baseline, data-access,
  security-review) now ends with the same one-line `next:` footer.
- The implement loop drives to a finish-grade bar by default (0.85, not
  CI's no-regression floor of 0.0) — a bar of zero once declared a 70%
  implementation done and handed it to the holdout, whose verdict then
  read a half-built system as a memorized exam. The holdout message now
  names both readings. When the agent command fails, the round log
  carries what the agent actually said, and the AgentMissing hint points
  at IDE-extension installs that bundle the binary off PATH.
- Prose recognisers from the demo's misses: "stays on this machine" /
  "stays local" read as data residency, "waits on each" as a person
  waiting, and receipts join the corpus-size vocabulary.
- The build receipt's exam count joins the worked example's transcript.

## [0.1.7] — 2026-09-10

- The implement fence no longer mistakes the interpreter for the agent:
  Python's own `__pycache__` bytecode, written beside `evals/taxonomy.py`
  on the first harness run, tripped the planted-file guardrail and stopped
  every real loop at round 1 with "the agent edited the exam". Found by
  the demonstration engagement's first live implement run; bytecode caches
  are now outside the fence, and the exam stays exactly as guarded.

## [0.1.6] — 2026-09-10

Found by the first full demonstration engagement — 626 real scanned
receipts (SROIE) run through the complete lifecycle on the published
wheel:

- `fde build <bare-name>` resolved the engagement but read the sample
  pairs from the raw argument's path, silently emitting a project with an
  empty golden set while sixty verified pairs sat on the engagement. The
  harness's empty-exam refusal caught it at runtime; now the path is
  resolved once, and the build receipt prints its own exam counts
  ("evals: 42 golden, …") with a pointed warning when pairs exist but
  none reached the golden set.
- The local-engine choice is a concurrency decision, not only a hardware
  one: `fde scan <engagement>` now reads the recorded arrival rate, and
  past ~1000 requests/day (where the gap between requests drops under a
  generation's length) it names the sequential-queue ceiling and the
  continuous-batching answer. The vllm and ollama stack entries carry the
  doctrine: paged KV admits more concurrent sequences, the scheduler
  retires requests mid-batch, and the crossover is measured, never guessed.

## [0.1.5] — 2026-09-10

Three independent fresh-eyes auditors ran against 0.1.4 the day it shipped
— an adversarial code review, a stranger following only the public docs,
and a claims audit. Everything they caught, in one release:

- The retrieval eval now grades every realization shape the registry can
  emit: a wired module-level instance wins over a fresh construction (a
  working deployment no longer scores 0% with the index blamed), class
  `run(query, top_k=…)` shapes are called correctly, and path-contract
  graph-retrieval is excluded from the recall gate it could never pass.
  Recall math hardened: duplicate relevant ids no longer inflate, wrong-
  shaped results are errors rather than silent zeros diluting a green CI.
- `graph-retrieval.qdrant`'s expansion loop yielded the wrong variable
  since v0.1.3 — the graph walk was dead code and the approach silently
  degraded to vector search. Fixed and pinned by executing the template.
  The graph-expanded variant survives adjacency entries for deleted
  documents (the continuous-churn case it exists for) and all three
  variants cap expansion breadth, not just depth.
- The emitted `ops/slo.md` now shows the captured baseline as the numbers
  to beat — it said "Not captured" over a recorded baseline, contradicting
  its own acceptance protocol. `evals/acceptance.md` stops citing a named
  eval owner when the client_readiness gate was waived, and stops citing
  "those 0" cases over an empty golden set.
- The architecture fingerprint now includes the topology: two engagements
  building byte-different projects (different boundaries) no longer share
  a fingerprint.
- The interview no longer re-asks a multi-valued question it just
  accepted; the offline_evaluability remedy names its clearing command;
  a rejection whose applies-condition references an unanswered dimension
  now names the question that could reverse it.
- Docs truth pass: the quickstart names all three gate steps before the
  passing build; the emitted-project tree shows `ops/diagnosis.md` and
  `evals/retrieval.py`; kb commands documented registry-free as they ship;
  README nav links absolute so they resolve on PyPI; ARCHITECTURE.md
  diagram says seven gates; CITATION.cff current; CI checks out full
  history so the sanitisation scan covers what the README says it covers.

## [0.1.4] — 2026-09-09

The measurement release: claims the framework already made, turned into
numbers and walks.

- Projects with a retrieval component ship `evals/retrieval.py`: recall@10
  and recall@50 against golden queries in `retrieval_cases.jsonl`, gated in
  CI, refusing an empty case set. The embedding and index choices set a
  ceiling nothing downstream recovers; this measures the ceiling by itself,
  no model in the loop. The diagnosis walk's evidence step now ends at this
  number, and both embedding approaches record the doctrine: chosen by
  measured recall on the engagement's own queries, never by leaderboard.
- Emitted projects ship `ops/diagnosis.md`: the walk that finds which layer
  a failure lives in -- definitions, evidence, tools, loop, model -- ordered
  cheapest-to-check first, sections adapted to the components actually in
  the system. An unclear definition can look like a model error; the
  expensive habit is re-prompting before finding out.
- Retrieval corpus: `corpus_churn` dimension (static/periodic/continuous —
  how fast the document stock turns over, distinct from corpus size and
  query arrival) and a graph-expanded-retrieval approach: vector entry,
  entity expansion, rerank exit, for multi-hop questions on a corpus that
  keeps changing. Full graph-retrieval now steps aside on continuous churn,
  by name, with the reason on the record. Realizations for plain-python,
  pgvector and qdrant.
- README quickstart shows the gate refusal before the passing build, so the
  first run's refusal is announced rather than a surprise.

## [0.1.3] — 2026-09-08

A post-launch funnel audit replayed every public transcript against the
shipped package; everything it caught, in one release:

- `fde start` with a statement now also offers the three questions worth
  asking next (the follow-ups hint names the actual engagement path).
- Seat economics dates its figures; `fde scan` on unified-memory machines
  no longer prints a contradictory "0GB total".
- Retrieval corpus: hybrid-search and reranked-retrieval (adopted by
  measurement, like finetune); LlamaIndex stack with a realization;
  invoices/complaints/claims join the corpus-size vocabulary.
- The worked example's transcript is now a replay test: an output change
  that would strand it fails in the same commit.
- CI tests 3.11/3.12/3.13; doc links absolute so PyPI renders them.

## [0.1.2] — 2026-09-07

A fresh-eyes usability round, every finding verified in a clean venv:

- The hero quickstart runs verbatim: bare engagement names resolve
  (`fde ask acme` finds `engagements/acme`), and `fde start` reads its
  own statement through the prose reader, so the first minute shows
  typed facts instead of "no facts recorded yet".
- `fde --version`; interview questions show their legal values with the
  question; gate remedies name their clearing commands; the baseline
  refusal names the exact keys that satisfy it.
- `fde implement` without an agent on PATH is a sentence with the fix,
  never a traceback; `fde cost --price-per-seat` works without fleet
  flags.
- kb subcommands take `--registry` (with `--root` kept as an alias).
- Every emitted project gets a front-door README; images are PNG so
  they render on PyPI and mobile; the README gains a copy-paste full
  lifecycle with the baseline YAML inline, and a Python API section
  backed by the public `fde.registry.default_root()`.

## [0.1.1] — 2026-09-06

- README images render everywhere: absolute URLs, because PyPI does not
  serve a repository's relative paths — and each release's page is frozen,
  so the fix required this patch.
- A terminal demo card on the front page, rendered from real output,
  refusal included on purpose.
- Social-preview image shipped in assets/.

## [0.1.0] — 2026-09-06

First public release on PyPI: `pip install fde-framework`. The registry
rides inside the wheel; a bare install knows everything the corpus knows.

### Added
- End-to-end pipeline: prose/document/sample/interview/hardware-scan intake →
  append-only fact log with dimension-dependent provenance → permutation
  space → seven gates (data access hard; baseline, readiness, scope drift,
  security review,
  offline evaluability, licence compatibility waivable with recorded
  reasons) → evidence-citing decision engine → architect → `fde build`
  emitting code, evals, deploy assets, ops runbook, `ARCHITECTURE.md` and
  `RISKS.md`.
- Hardware scan (`fde scan`) with measurement-only DETECTED provenance and
  silicon-gated optimisation advice; dated costing (`fde cost`) with the
  naive figure beside the real one.
- Evolution loop: overrides honoured on the next run, build-time
  predictions, `fde observe` → trigger calibration, `fde retro` case
  capture, human-gated `fde kb ingest-case` (cases land
  `sanitization: pending`; CI refuses pending).
- Registry tooling: `fde kb validate` (cross-links, topology vocabulary),
  `fde kb gaps` (work items: evidence stubs, unweighted dimensions, stale
  stacks), `fde kb sweep` (profile shapes no approach can serve, each with
  a reproducing example).
- Knowledge registry: 26 dimensions, 49 approaches, 53 patterns, 14 stacks,
  16 components, 2 locales, 70+ templates — all data, no code.
- Scope axes on every dimension (functional, non-functional, data,
  environment, operational, commercial): `fde status` and the emitted
  architecture document group by them, and `fde ask --scope` runs one axis
  at a time.
- Hybrid as a first-class hosting topology, with the boundary between the
  two halves enforced in emitted code.
- Locale packs (`fde locale`): jurisdiction presets at weakest provenance
  plus dated obligations emitted as COMPLIANCE.md.
- `fde reuse`: the client's existing stack outranks adoption when it serves.
- A security-review gate: a system living in the client's environment or
  touching their systems blocks until their security function has seen it
  (`fde security-review`), because the review nobody scheduled is the
  engagement-killer every public playbook names.
- `arrival_rate` and `availability_target` dimensions: flow sizing read by
  `fde cost --root`, and an availability target the emitted slo.md carries.
- Emitted `evals/acceptance.md` (blind user-acceptance protocol) and
  `evals/load.py` (p95 against the stated budget; fails until the pipeline
  is implemented, like the harness).
- `access_model` moves the governance decision (role-scoped authority),
  `sensitivity_present` earns a redaction component in the crossed case
  (sensitive fields, data free to leave), and `fde triage` ranks candidate
  problems by decidability, honestly labelled.
- `fde frame --reader llm`: a model proposes facts for what the
  deterministic reader left open -- validated against the registry,
  landing at weakest provenance, hosted path refused unless data may
  leave, local OpenAI-compatible endpoints always allowed.
- Multi-modal input: input_format holds peers (photos AND documents AND
  telemetry, voice, video); perception fans one instance per modality.
- Judge-based evaluation reaches the emitted harness: freeform systems
  are graded by model comparison against the reference via app/llm.py
  (local endpoint first-class; hosted refused inside a boundary).
- fde cost unit economics (--price-per-seat): cost per workflow against
  revenue per seat, with the cascade/caching/loop-bound levers priced.
- fde scan recommends a local runtime and models sized to the measured
  hardware, dated.
- fde implement --holdout: cases the delivery never shipped, against
  memorized greens.
- The LLM as proposer at every seam: fde kb suggest mines briefs for
  recogniser gaps (verbatim-citation guard, boundary-gated), fde frame
  retains briefs so spans stay meaningful, and fde kb export-training
  builds the fine-tune corpus -- adoption governed by the corpus's own
  finetune rule.
- Emitted code carries the engagement's numbers: templates receive the
  settled profile, and a build ends by naming its finishing move
  (fde implement, with the holdout when one exists).
- `fde implement`: drives a coding agent until the emitted evals pass,
  with the evals, boundary, controls and decision documents hashed as a
  fence -- an agent that edits the exam is caught, reverted, and stopped.
- Sanitisation gate in CI: allowed paths only, history scan, credential and
  PII patterns, denylist, no AI attribution, no pending cases.

### Hardened
- Three adversarial review rounds (2026-08-26 → 2026-08-27): 54 findings in
  round one, 39 in round two, 15 in round three, every fix pinned by a
  regression test. Includes closing a hard-gate bypass (zero-width-space
  attestations), a path traversal in case ingestion, markdown injection in
  the generated risk page, and an emitted critic that ran after the
  irreversible step it guards.

## [0.1.0] — unreleased target
First tagged release. The repository is public under Apache 2.0.
