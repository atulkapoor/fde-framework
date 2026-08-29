# Changelog

Notable changes, oldest last. Format follows [Keep a Changelog](https://keepachangelog.com/);
the project is pre-release, so everything sits under 0.1.0 until the first tag.

## [Unreleased]

### Added
- End-to-end pipeline: prose/document/sample/interview/hardware-scan intake →
  append-only fact log with dimension-dependent provenance → permutation
  space → six gates (data access hard; baseline, readiness, scope drift,
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
- Knowledge registry: 22 dimensions, 43 approaches, 48 patterns, 12 stacks,
  60+ templates — all data, no code.
- Scope axes on every dimension (functional, non-functional, data,
  environment, operational, commercial): `fde status` and the emitted
  architecture document group by them, and `fde ask --scope` runs one axis
  at a time.
- Hybrid as a first-class hosting topology, with the boundary between the
  two halves enforced in emitted code.
- Locale packs (`fde locale`): jurisdiction presets at weakest provenance
  plus dated obligations emitted as COMPLIANCE.md.
- `fde reuse`: the client's existing stack outranks adoption when it serves.
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
