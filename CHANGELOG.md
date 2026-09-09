# Changelog

Notable changes, oldest last. Format follows [Keep a Changelog](https://keepachangelog.com/);
the project is pre-release, so everything sits under 0.1.0 until the first tag.

## [Unreleased]

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
