# Changelog

Notable changes, oldest last. Format follows [Keep a Changelog](https://keepachangelog.com/);
the project is pre-release, so everything sits under 0.1.0 until the first tag.

## [Unreleased]

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
