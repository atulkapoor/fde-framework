# Changelog

Notable changes, oldest last. Format follows [Keep a Changelog](https://keepachangelog.com/);
the project is pre-release, so everything sits under 0.1.0 until the first tag.

## [Unreleased]

## [0.1.30] — 2026-09-20

A second outside reading, this time of the source, agreed with the
README's own verdict -- built and demonstrated, not proven -- and named
the gap that is not another feature: the causal chain from a business
outcome to an architecture, and the assumptions an engagement quietly
rests on. This release makes both legible on the record.

- **The eighth gate: an outcome contract.** `fde outcome-contract`
  records who owns the number the system exists to move, what it is,
  its value today, its target, how it is measured and over what window.
  Nothing builds until that is on the record or waived with a reason that
  ships in RISKS.md; a target nobody set is refused rather than filled
  in. The adoption stage reads the contracted metric back from what was
  measured in the field.
- **Decision debt.** `fde debt` lists everything the engagement rests on
  that nobody has settled: a gate still failing, a waiver standing in for
  a condition, a fact the framework guessed or a person merely said where
  a measurement was possible, two people disagreeing, an attestation with
  nobody's name on it, a role never asked, an incident open, a component
  nothing serves -- each with an owner, what it blocks, and its age.
- **`fde next` says what hangs on the question.** When the next move is
  an interview question, the command prints the evidence already on
  record for that dimension, every candidate answer tried as the
  framework's own guess, and the decisions that turn on it.
- **The claim ladder.** The README's status is now six claims, each
  marked verified, partial or unverified with the evidence and where it
  stops, so the project cannot be over-read in either direction.
- The example walkthroughs and their pinned transcripts carry the eighth
  gate.

## [0.1.29] — 2026-09-20

The operating loop from 0.1.28 has now run in public: on the banking
demo, two field streams through the delivered build, a drift incident
opened and closed on the record, a value document. This release adds
the layers around it that could be built honestly without a client.

- **The stakeholder map.** `fde stakeholders` reads the engagement's
  people off the record: which of the five roles has been heard (every
  session carries the role and, when given, the name), who signed what,
  which roles were never asked, and what is on the record with nobody's
  name on it. `fde stakeholder add` names the people who have not spoken
  yet. It is a map, not a contact list.
- **Names on the record.** `--by` on `data-access`, `security-review`,
  `waive`, `deployed`, `outcome` and `incident close` records who signed;
  the entry is honest state without it, and the map points at it.
- **Exports as the connector.** `fde import` turns a client export --
  csv, tsv, jsonl, json, the client's column names -- into the pairs the
  intake reads, and reports what it kept, skipped, dropped as duplicate
  and counts as verified. Nothing is verified unless the caller says
  which column and value means a person checked it. Live connectors are
  not here: an export is what a client can hand over inside their own
  boundary, and the only interface testable without their credentials.
- **A bench, not a benchmark.** `fde bench` reads the same figures off
  every engagement record side by side -- stage, the out-of-sample rows,
  the gap, incidents, days to pilot -- and writes `BENCH.md`, which says
  how many rows it has. The repository's own `BENCH.md` is the four
  public demos.
- **The history page.** `fde history` prints every dated entry on the
  record in order, the undated ones above it, one line each.

## [0.1.28] — 2026-09-20

An outside reading of the repository put it plainly: a strong engineering
framework, not yet an operating system for the engagement, because the
record stopped at the build. This release carries the record through
deployment, the field, and the client's figures. Nothing in it is
declared by the tool; each fact is computed from evidence or attested by
a named person.

- **The stage is computed, never declared.** `fde stage` reads the record
  against per-stage criteria -- discovery, validation, prototype, pilot,
  production, adoption, retrospective -- and appends each transition to
  `lifecycle.jsonl` with its evidence. Production needs a deployment on
  record and no open incident; adoption needs a figure measured in the
  field; retrospective needs a case. `fde outcomes` prints what the trail
  shows: transitions, days to pilot, loop rounds, reversals, incidents.
- **The field is read against the exam.** `fde drift` reads the deployed
  service's journal -- the `answered` lines it already writes -- and
  compares abstention, decision mix, errors and margins with the golden
  set and the last scorecard. Past a threshold it opens an incident on
  the record and exits 1; an open incident pulls production back to
  pilot until `fde incident close` records what was done. Fewer than
  thirty events is a sample of nothing, said as such.
- **Value in the client's own figures.** `fde value` writes `VALUE.md`
  from the recorded baseline and the holdout row: automated share,
  accuracy on the automated, residual human work, errors added and
  removed, hours and money, build and run cost, payback, a Wilson
  interval on the accuracy. Every line carries its basis -- measured,
  stated, assumed, derived -- and the document names the stated and
  assumed lines before any total.
- **Attestations, not inferences.** `fde deployed` and `fde outcome`
  record where the system runs and what the client measured; the
  lifecycle reads them and nothing infers them from a build.
- The README says what the operating loop still is not: a stakeholder
  graph, enterprise connectors, a benchmark of engagements. Those need
  engagements that have not happened yet.

## [0.1.27] — 2026-09-19

The ninth pass reproduced every number 0.1.26 printed and showed what
they hid: the scorecard measured self-consistency, not fitness, and the
banking deliverable routed a greeting to the commonest queue with a
0.02-nat margin. Each finding is a check before it is a fix.

- **The scorecard has fitness rows.** A generalisation-gap row (golden
  in-sample minus holdout, capped at twenty points); an external-exam row
  (`--external <jsonl>`, a second out-of-sample set nobody at the
  engagement chose -- the row a component that memorises the golden and
  holdout files cannot pass); a "beats the baseline error rate" row read
  from the engagement's recorded baseline; a valid request through the
  edge, and whether the answer says why; readiness judged where nothing
  external is needed; a regression row against the last card; floors on
  the edge and adversarial layers. The card says which rows are fitness
  and which are self-consistency, and that the service was booted on the
  measuring machine, not in the unit.
- **The baseline abstains and explains.** Below a top-two margin
  (`ABSTAIN_MARGIN`, default 0.5 nats) the labelled-decision baseline
  answers `unknown` and says it abstained; the harness reports the
  abstained share and the accuracy on what was answered; every routed
  answer carries the top labels with scores, the margin and the tokens
  that carried it, in the response and in the journal. A build with no
  model seam no longer turns every valid request into a 500 when a model
  endpoint sits in its environment. A scaffold answers 501 by name, never
  a bare 500.
- **A label is stripped only where it is dictated.** Quoted, braced, or
  after an instruction cue. Stripping every occurrence cost two points on
  real customers who were stating the intent in their own words.
- **The loop's fence covers the tests and the contract.** An agent that
  deleted the lint test and hollowed out `app/contract.py` once reported
  green with no violation. The shipped baseline's holdout is measured
  before any round, and a round that lands below it is refused: it
  traded generalisation for the exam.
- **The decision shape survives one rare label.** Nine in ten pairs
  carrying a repeated value is a label set; a singleton intent is learned
  from, never held out. A definition that says "stated" is marked stated.
- **The banking run, again, under these rules.** Rebuilt on 0.1.27 the
  shipped baseline abstains on 16% of the holdout and answers 87.9% of the
  rest correctly, a tenth of a point under the bank's recorded 88%
  first-pass accuracy; the implement loop, fenced and guarded, took the
  holdout from 73.7% to 77.5% in two rounds. At a one-nat margin the
  finished deliverable answers 90.2% of what it routes correctly and hands
  18% to a person: the engagement's bar is met in assist mode and the card
  says so, with the vendor's own test split as the external exam beside
  it. It is not an autonomous router, and nothing on the card claims it is.

## [0.1.26] — 2026-09-19

Production grade, measured, and a first industry use case run end to end.

- **`fde scorecard <project> [--holdout <jsonl>]`.** One command runs
  what a deliverable can prove about itself and writes `SCORECARD.md`
  beside it: its own tests, lint, every exam layer against its majority
  rate with the in-sample layer marked, the harness's own verdict, judge
  calibration, the holdout with the acceptance protocol's sample floor
  and the digest on record, the exam record, the edge probed by booting
  the service (identity, forged result, forged identity, malformed body,
  readiness), the risk register, the environment, the training path.
  The verdict is a count of rows -- "16 of 17 measured properties hold"
  -- and a property the build cannot measure is n/a, never a pass.
- **The out-of-sample CI lane.** A second job scores the engagement's
  holdout where it lives, on a self-hosted runner that holds the file at
  the path `HOLDOUT_PATH` names; until it is configured the golden score
  is the only one CI sees, and the README says so.
- **A text decision with a labelled history is labelled-decision at any
  labelled count.** Classical ML avoids free text: routed there, a text
  decision met a component that asked for numeric features. The label
  set may run to five hundred.
- **What routing a retail bank's support intents found.** A one-field
  output was read as a decision only up to five distinct values, so
  seventy-seven intents built with no reasoning component and an exam at
  0.0%; a label set is now recognised by repetition. "Routed to",
  "triage" and "by intent" read as a decision. A label joined by
  underscores is stripped the way it tokenises (an injection naming
  `card_payment_fee_charged` was followed until it was). The
  role-scoped-authority template failed lint, and no acceptance shape had
  ever emitted it: a routing shape joins the suite (five shapes now).
- **What the implement loop found on the same run.** The loop scored the
  holdout against the golden bar, and the golden score is in-sample
  wherever the baseline is fitted on it: an implementation that had
  raised the holdout by three points was refused as "memorised". The
  holdout is now scored against the harness's own gate (the majority
  rate, the exclusive half-right floor) with the golden bar stripped. And
  the loop's check was the harness alone, so a round could leave a lint
  error behind a green exam: the deliverable's own tests -- now including
  lint wherever ruff is installed -- run first, as the floor beneath the
  harness. Under the corrected gate the loop finished green in two rounds,
  and `fde scorecard` reports 17 of 17 measured properties holding: golden
  95.4% in-sample, holdout 81.3% on 3,036 cases never shipped, 80.2% on
  the vendor's own 3,079-case test split, every adversarial probe passed.

## [0.1.25] — 2026-09-19

The eighth pass gave the decision shape its first sign-off, with
conditions, and refused the fine-tuning path on named ones. It also
found that two 0.1.24 fixes were shaped to the one demo. Each is a
check before it is a fix.

- **A label written out in full is not evidence; its words may be.**
  Dropping every word of every label from the vocabulary cost a
  refund/escalate/reply corpus a third of its accuracy, because there the
  label word is the cue. The full label phrase is stripped from the text
  instead; single words stay evidence. The docstring says what a
  bag-of-words baseline cannot defend: content that repeats a label's
  strongest cues.
- **Probe bases are typical cases, one per label, at the median length.**
  Built on the two shortest inputs, every probe on the demo sat on a case
  the baseline misreads, and "0 injections followed" read as a pass while
  measuring nothing. The bases ship in the edge layer (so each is scored
  un-steered) and leave golden. When every base is still misread, the
  harness says no probe was scorable rather than printing a takers count;
  a steered probe answered with a third label counts as wrong under
  mutation, not as a misread.
- **The merge path trained one epoch and saved zeros.** Merging inside
  the loop left the optimizer holding the old adapter tensors; the saved
  adapter's B matrices were exactly zero under a versioned name. The best
  adapter is now merged from disk onto a fresh base after training, and a
  real-weights pin (`tests/test_finetune_real.py`, run where torch is
  installed) proves the merge path trains what the plain path trains.
- **The recipe learned from the run.** Padded batches with the padding
  masked out of attention and loss, linear warm-up and cosine decay,
  gradient clipping at 1.0, adapted modules chosen per architecture by
  peft unless overridden (a hard-coded Llama list refused every other
  family), the optimizer-step count and schedule on the record.
- **The comparison says what it can and cannot claim.** A form score --
  the share of answers that open the way the verified answers open --
  beside the judge's score, in every layer and in the comparison record;
  `quotable: false` with the reason when the holdout has fewer than
  thirty cases or the judge is uncalibrated; a delta on too few cases is
  refused unless asked for as a smoke test. The floor in force
  (`--min-verified`) and the environment that trained (device, dtype,
  library versions, base revision) are on the record. Evidence is
  attached with the pipeline's own default `k`.
- **Boot refusals that were missing.** A fine-tune build without
  `FINETUNED_MODEL` refuses to boot instead of answering 503 to every
  request; a labelled-decision build without `evals/manifest.json` refuses
  rather than serve an unverifiable fit; the holdout path notes a file
  that is not the recorded one and an uncalibrated judge.

## [0.1.24] — 2026-09-19

The two findings the 0.1.23 demo eval left open, and what a first real
training run found once the recipe met a GPU-less machine, a base model
and a judge.

- **A label named in the text is not evidence.** The labels' own words
  are excluded from the baseline's vocabulary, so an injection that
  spells a label out cannot steer the decision -- the one followed
  injection on the demo. A steer whose wrong answer merely coincides
  with a misread base is reported as a misread, not a follower.
- **The recipe trained, served and was compared, for real.** SmolLM2-135M
  on CPU, eighteen house-style pairs with retrieved evidence: holdout loss
  fell every epoch to 1.77, four of six unseen answers came back in the
  house style the base model never produces, and the comparison measured
  +16.7 points under an independent judge. What that run found, fixed
  here: the harness never loaded the corpus, so a retrieval build was
  scored without evidence (it loads it now, and says when there is none);
  a model name with a slash became a directory in the comparison's file
  names; generation ran on into the next imagined question (stop
  sequences are sent and applied, in the component and in the shim); a
  judge that thinks was capped at the author's token budget and never
  reached a verdict (`JUDGE_MAX_TOKENS`, default 1024); seven optimizer
  steps trained nothing (the step count is on the record with a floor
  warned about, and accumulation is a flag); zero against zero exited
  green as "not worse" (it is "no signal" now, non-zero). `train/serve.py`
  puts the base model and an adapter behind the production wire shape in
  process, so the comparison runs on the machine that trained.

## [0.1.23] — 2026-09-19

The seventh pass re-ran every 0.1.22 check and found them holding -- the
edge, the exam record, the judge gates, the mapper -- and turned up where
the shape-specific work stopped short: the labelled-decision baseline and
the fine-tuning path. Each finding is a check before it is a fix.

- **The fitted baseline is a multinomial naive Bayes, and it refuses to
  serve a constant.** The estimator that shipped charged every unseen
  token a per-label absence cost, drifted long inputs to the rarest
  class, and recalled the commonest label once in sixteen on the
  holdout; on the same tokens the multinomial form scores fifteen points
  higher. Without a golden file to fit on the old component answered the
  first label to every request behind a green `/ready`; construction now
  refuses (exit 78, one line), and because the served model is fitted on
  the exam, a golden file whose digest is not the recorded one refuses
  the boot until the exam record matches. `decided_by` names who chose.
- **On-sample and off-sample, told apart.** The harness marks the golden
  score in-sample wherever the baseline is fitted on it, and the holdout
  path (`--cases`) now carries per-class metrics and the majority gate --
  the out-of-sample number is the one that has to clear it. The majority
  rate is compared unrounded: a constant answer scores exactly the
  majority, and rounding once let 11/29 clear a gate set at 0.379.
- **Probes and edges come from cases the baseline was not fitted on.**
  Edge cases move out of golden rather than being copied (counted once,
  scored out-of-sample) wherever golden keeps a floor; the adversarial
  probes build on them; each steering probe records `steered_toward`,
  and the harness reports an injection as followed only when the answer
  IS the injected one -- a wrong answer that is not it is a misread of
  the base case, and the verdict says which.
- **The split counts one case once and holds every label out in the same
  share.** `split_pairs` drops exact repeats of an earlier input and
  stratifies by label when the outputs are a label set; a freeform
  corpus stays one stratum, because five answers for five pairs are
  answers.
- **The fine-tuning path trains on the shape it serves.** `prepare.py
  --retrieve` attaches the deliverable's own retriever's hits to each
  pair; the recipe refuses pairs without evidence in a build that serves
  with it, refuses an empty holdout, tokenises prompt and completion
  separately with the prompt truncated from the left so the completion is
  always present, seeds and shuffles every epoch, measures holdout loss
  per epoch and keeps the best adapter. The serving side posts to
  `/v1/completions` with the raw prompt, so no chat template is wrapped
  around tokens the recipe never produced; `/ready` names an adapter the
  endpoint does not serve; the judge treats `FINETUNED_MODEL` as the
  author. `compare.py` exits non-zero when either side errored: both
  sides erroring on every case once produced a delta of +0.0% and a
  green exit.
- **The request contract is per approach.** A text decision no longer
  accepts a solver's `items` and `capacity` or another perception's
  `pages`, `rows`, `events`. `text` and `documents[].text` are capped at
  the same bound as a bare string. A forged `principal` or `request_id`
  is refused by name, like a forged result. Two documents to a
  one-decision path are one refusal, not one silent decision. An
  approval-gate refusal is written to the ledger. The optimisation
  planner refuses a negative size.
- **RISKS.md marks scaffolds by a marker, not a substring.** A fitted
  classifier was listed as "not yet implemented" because it raised
  NotImplementedError for a real reason. The emitted `.gitignore` keeps
  `.ruff_cache/`, `.pytest_cache/`, `train/data/` and `artifacts/` out of
  history. `fde samples` advertises only the metrics the harness computes.

## [0.1.22] — 2026-09-18

The sixth pass, widened past the edge to the exam, the components and the
fine-tuning path, signed off the freeform shape with conditions and
refused the decision shape for reasons that were the generator's. This
release answers each as a check first.

- **A decision read off labelled text ships a classifier, not a solver.**
  A hundred and twenty complaints once reached a constraint solver with
  nothing to optimise and a planning step that 500'd on caller input. A
  new `labelled-decision` approach applies to a decision over text with a
  labelled history: the emitted component names the client's labels,
  fits token log-odds on the golden set at import, decides with a
  per-label score, and refuses to exist without labels rather than
  scaffold. Optimisation is ruled out for text input on the record; the
  plan for a text decision is a fixed sequence. The optimisation planner
  validates every caller key and its `Infeasible` is a refusal (4xx).
- **A constant answer is not a passing grade.** The harness computes
  per-class precision, recall, F1, the confusion and the majority rate
  for any decision task, and the golden layer is red when the score does
  not beat the majority. A label is its label whichever way it is
  written -- a classifier right on every case once scored 0.0% because
  the pairs said `{"decision": "refund"}` and the pipeline said `refund`.
- **The exam steers.** Two probes join the adversarial floor: the other
  case's input steered toward this case's answer, and this case's input
  steered toward the other's -- each graded against the original label,
  so a system that follows the injection fails both and a constant
  answer fails one. Empty, whitespace, oversized, wrong-type and
  control-character probes join for string inputs; edges are derived
  from the data when no pair is tagged.
- **The exam record.** `evals/manifest.json` and the acceptance
  protocol carry the split seed, the holdout share and the SHA-256 of
  every eval file and of the engagement's holdout; `fde implement` names
  a holdout that is not the recorded one, and `fde samples` announces a
  replaced holdout with both digests. 36 verified pairs once went missing
  between the split and the shipped holdout and nothing could say so.
- **An uncalibrated judge is red until asked for by name.** The judged
  harness refuses to pass without a calibration record unless
  `--allow-uncalibrated` asks for a provisional score; `fde implement`
  passes it and marks the report provisional. A line that labels itself
  a verdict outranks the rationale around it. The same-model judge is
  refused. `field_coverage` is no longer advertised where it is never
  computed.
- **The fine-tuning path is a path, not a sketch.** A finetune decision
  now emits `train/`: a seeded, stratified, de-duplicated split with
  every digest recorded (`prepare.py`), a LoRA recipe on `peft` that
  refuses data whose digest changed and names the adapter by what went
  into it (`lora.py`), a before/after comparison on the holdout the
  split held back through the deliverable's own harness (`compare.py`),
  and model-free tests of all three that the deliverable's CI runs. The
  serving side answers through `FINETUNED_MODEL` in the exact prompt
  shape the recipe imports, and refuses without an adapter -- it no
  longer returns a data split as an answer. `peft` joins the stacks.
- **Facts this design stands on.** RISKS.md lists the boundary-bearing
  dimensions with their provenance; a residency learned in an interview
  is marked asserted, not established. A baseline figure whose
  definition calls itself an estimate or a scenario is marked stated,
  not measured, on the SLO page.
- Also: the deterministic mapper takes its contract from configuration
  and preserves the text it was given; `mapped_share` is `None` rather
  than a vacuous 100% when there is nothing to map; the fixed-sequence
  and optimisation planners return the envelope; the sample assessment
  warns on exact duplicates, conflicting labels and a truncation
  cluster; `LLM_API_KEY` is documented; the labelled-decision and
  fine-tuning realisations are pinned in `tests/test_acceptance.py` and
  `tests/test_finetune.py`.

## [0.1.21] — 2026-09-18

The fifth-pass audit returned the first sign-off, with conditions. Two
were the framework's, both narrow, both verified by running them; this
release meets them, checks first. (The other two are the engagement's:
sizing the corpus ceiling and the unit's memory cap together for the
stated scale, and seeding the eval sets from the client's own pairs
before any score is quoted.)

- **A truncated query is never a silent miss.** The truncation note was
  appended only on the success path, so a query cut at the token cap
  that then matched nothing read byte-for-byte like a genuine miss. The
  note is now on every path, with the cap it was cut to.
- **Two processes cannot both reserve one key.** `reserve()` checked
  only its own process's snapshot under a thread lock; a second ledger
  on the same STATE_DIR -- a debug run beside the unit, a failover
  before the old instance is dead -- could take a key already taken.
  Reservation now re-reads the file under the same cross-process
  directory lock compaction uses, and exactly one caller owns the key.

The audit loop in numbers: five independent passes on successive
emissions, criticals 5 → 2 → 1 → 0 → 0, highs 11 → 9 → 3 → 4 → 0, and
every class of finding pinned in the acceptance suite before its fix.

## [0.1.20] — 2026-09-18

The fourth-pass audit was the first to name the exact conditions for
sign-off. Four of its six were framework defects, one of them mine from
the round before; this release meets them, checks first. (The other two
-- seeding an engagement's eval cases, and running the deliverable's
edge tests in CI -- are an engagement's inputs and a one-line workflow
fix, the latter shipped here.)

- **The stopword cut became a recall cliff, and is gone.** A token in
  most documents was discarded outright, so a one-document corpus
  retrieved nothing for any question and a homogeneous corpus retrieved
  nothing for its own domain word. Tokens are now three kinds:
  informative (a minority of documents) rank alone when any matches;
  ubiquitous ones rank, weakly, when none does; function words never
  count. Every result carries a `retrieval_note` saying which case it
  was, so "I don't know" for a genuine miss is never the same sentence
  as "I discarded your question". The query cap rose to 512 tokens and
  truncation is noted.
- **One non-object corpus record no longer exits 1.** The skip path
  itself assumed an object; it now names the record's type, and the
  corpus load is wrapped so any escape is one line and exit 78 --
  never a restart loop.
- **Compaction races the running service no more.** Every ledger write
  and the operator's `compact` take an exclusive lock on `STATE_DIR`;
  compaction re-reads the file under that lock before rewriting it, so a
  key reserved by the service a moment ago survives (the earlier version
  rewrote from a stale snapshot and dropped it); the temp file and the
  directory are fsync'd.
- **Every eval entry point imports the boundary.** `evals/calibrate.py`
  was the one script that sent references and answers to a judge without
  it; both it and the harness now refuse an outside judge with one line
  and exit 78.
- Authorisation denials -- unregistered tool, scope not held, arguments
  refused -- leave an audit record. A request line that never parses is
  a JSON 400 with an id, not a bare body without a status line. Every
  log line carries the client address (`TRUSTED_PROXY=1` trusts the
  forwarded one). `/ready` lists degraded files only to a bearer.
  `goal` is an alias of `query`; `from`/`to` are accepted only by graph
  retrieval. The verdict parser reads "Verdict: correct" as a verdict.
  The sizing figure is restated as the measured range (five to
  twenty-five MB per MB of text, by vocabulary). CI runs every test in
  the deliverable, edge included.

Deferred, named: postings on disk above the ceiling; per-caller
identity; the MCP variant's audit; taxonomy reachability; SHA-pinned
actions; re-running the public demos on this emitter.

## [0.1.19] — 2026-09-18

The third-pass audit found the edge, the boundary, the ledger, the gates
and the evals holding under attack, and one number nobody had reconciled:
the lexical index costs about twenty megabytes of memory per megabyte of
corpus text, so the stated corpus would have been OOM-killed by the unit's
own cap before the socket opened. This release closes that layer, checks
first, and every deliverable now defends its own edge.

- **Sizing is a decision, written down.** `CORPUS_MAX_MB` and the unit's
  `MemoryMax` are one decision, documented together with the measured
  rate in ARCHITECTURE.md, the env file and the unit; a corpus over the
  ceiling refuses the boot with one line (exit 78) instead of dying to
  the OOM killer. The index dropped its per-document token counters --
  half its footprint -- and `TasksMax` is sized against
  `MAX_BODY_BYTES` so bodies in flight are inside the budget.
- **A stopword is not evidence.** Retrieval is BM25 over the postings,
  every hit carries its score, and a token found in more than half the
  corpus cannot make a document relevant on its own -- "How do I reset
  the payroll database?" no longer cites an HTTP document on the
  strength of "the"; it answers "I don't know."
- **The request contract is this build's.** `CALLER_KEYS` is generated
  from the components on the request path: a key nothing reads is
  refused by name, so a caller who sends `documents` to a build that
  ingests at boot gets a 422, not a confident answer from another corpus.
- **Readiness tells the truth in both directions.** Skipped corpus files
  DEGRADE `/ready` (listed on the 200 body) rather than denying it; more
  than half unreadable denies. The first poll always probes (the cache
  was seeded fresh-and-clean, a false green inside the first seconds of
  uptime). A gateway answering a list at `/v1/models` is a named 503,
  never a dropped socket. One malformed `.jsonl` line loses one record,
  not the file.
- **Every refusal is exit 78 and one line**: a boundary violation, an
  unresolvable `BIND`, a port in use, an unwritable state dir, an
  oversized corpus. `169.254.169.254` -- the cloud metadata address,
  which Python counts as private -- is outside the boundary.
- **The judge may not be the author under another name**: the harness
  compares the resolved (endpoint, model) pair, so `JUDGE_ENDPOINT` set
  to the same URL is refused like an unset one. A holdout exactly half
  right is red.
- **The deliverable defends its own edge**: `tests/test_edge.py` boots
  the service on an ephemeral port and asserts every promise
  `app/service.py` makes -- 401 without a token, forged keys refused,
  request ids matching headers, strict framing, close-after-error, a
  named readiness problem, a clean drain, exit 78 on a bad port.
- The ledger's `idempotency.jsonl` is COMPACTED, never rotated (a key
  rotated away is an action that can happen twice): `python -m
  app.ledger compact --keep-days 90`, in the runbook. Framing rejections
  carry a request id; every stderr line the pipeline and ledger write is
  one write.

Deferred, named: postings on disk (SQLite FTS5) above the sized ceiling;
per-caller identity; the MCP variant's audit; taxonomy reachability;
SHA-pinned actions; re-running the public demos on this emitter.

## [0.1.18] — 2026-09-18

The second-pass audit of 0.1.17 — same principal-engineer lens, no memory
of the first round — confirmed the first-round criticals gone and found
the layer underneath, every item verified by running it. This release
answers that layer, checks first:

- **A caller could forge an answer.** `known` and `act` rode in on the
  request and `reasoning` returned `known[question]` as grounded, HTTP
  200. The request contract is now an ALLOWLIST (`CALLER_KEYS` in
  `app/shapes.py`): any key a step writes is refused by name when a
  caller sends it. Questions are capped in length; `k` is bounded.
- **The CPU denial of service had moved, not gone.** Retrieval scanned
  every chunk for every query token — 5.7s per POST at a tenth of the
  stated corpus. The lexical tier now keeps a postings list per token and
  caps query tokens; a 3000-token query over 6000 chunks costs
  milliseconds, and the acceptance suite times it.
- **The journal interleaved under threads** (41% of lines unparseable
  at eight workers): one locked write per line. **The audit misattributed
  request ids** on the shared component: the id is passed through the
  call, never stored on the instance. **Argument values** no longer go to
  disk by default — keys and a digest do (`AUDIT_ARGUMENTS=full` opts in).
- **Errors answered before the body was read desynchronised keep-alive**
  (the unread body became the next request line): every 4xx/5xx closes
  the connection. The body is read before a worker slot is taken, so
  eight trickling sockets no longer make every real request a 503. Idle
  keep-alives time out in ten seconds, so a drain does too.
- **One bad corpus file crash-looped the boot**; unsupported and
  mis-cased files were skipped silently. Every file is read under its own
  try, skipped files are named in the boot log and counted in `/ready`,
  suffixes are case-insensitive, and a corpus update is a documented
  restart.
- **A torn ledger line made the process unbootable**, and an unwritable
  `STATE_DIR` was a traceback: torn lines are skipped and counted, writes
  are one `O_APPEND` syscall, an unwritable state dir is one clear line
  and exit 78, numeric keys are canonicalised (100 and 100.0 are one
  payment), and a stuck key has a procedure: `python -m app.ledger
  resolve`, in the runbook.
- **An unapproved action paid for a model call first**: gates and critics
  now run first on the request path. Authorisation failures answer 403,
  a control's refusal 409, an unknown tool 400 — never 500. Answers carry
  their `sources` and `stopped_because`.
- **The judge may not be the author**: a judged run refuses unless
  `JUDGE_ENDPOINT`/`JUDGE_MODEL` name a different one or
  `ALLOW_SELF_JUDGE=1` accepts it by name; CI passes the judge variables.
- **The documents run as written**: the README's local run sets what the
  edge requires; the install stages the corpus; `RestartPreventExitStatus=78`
  so a refused configuration is not restarted; ARCHITECTURE marks advisory
  components and says the tool boundary ships unwired; RISKS records the
  single shared principal. The boundary no longer trusts `.internal` /
  `.local` suffixes — a host is inside only when named or private.
- **A test caught what would have shipped**: the new `python -m
  app.service` entrypoint had no `__main__` guard; the unit would have
  started a process that exited 0. Perception's column detection is a
  linear scan too; hybrid-search exposes `fuse()` and keyword-search
  carries no fusion it does not use.

Deferred, named: index memory footprint at the stated corpus size (store
offsets, not duplicated chunk text); per-caller identity; ledger rotation
and compaction; the MCP variant's audit; three taxonomy sources the
harness cannot reach; SHA-pinned actions.

## [0.1.17] — 2026-09-18

Four independent fresh-eyes audits of the 0.1.16 output — a principal
engineer signing off a deliverable, a security red team, a maintainer
inheriting it for two years, and a client staff engineer reviewing a
shipped demo — converged on one diagnosis: essays with disconnected code.
Components did not compose (the freeform build answered every request
with a 500), controls could not fire, ledgers lived in RAM, nothing ever
refused input, and the boundary was a placement table while the real
egress had no host check. This release is the answer. Every class of
finding became an acceptance check before it became a fix.

- **The seams.** `app/shapes.py` is one envelope every step reads and
  writes; steps return `{**payload, ...}`, never a fresh dict. The
  pipeline orders steps by phase (what reads before what chunks before
  what indexes; nothing outward before reasoning decides), splits an
  ingest path from the request path where a retrieval layer exists,
  loads the corpus from `CORPUS_DIR` at boot, and picks the OUTPUT the
  caller gets back. Garbage is refused at the door with the reason.
  Approval gates and critics apply to actions and pass everything else.
- **The edge.** `app/service.py`, importable and tested: bearer-token
  identity with the principal set from configuration (a body cannot
  grant itself a scope); a request id on every log line and every
  response, refusals included; strict framing (one decimal
  Content-Length, no transfer-encoding, nested-JSON bombs are a 400);
  bounded workers with a 503 on saturation; HTTP/1.1; no exception text
  in any response; transient failures classified by type; configuration
  validated once and refused with exit 78; `/ready` cached, loopback-or-
  token, checking the model is actually served; SIGTERM drains.
- **The boundary is code.** `app/boundary.py` validates every outward
  URL at import — loopback, private ranges, or a named host — and refuses
  `ANTHROPIC_API_KEY` outright; the unit adds `IPAddressDeny`/`Allow`.
- **A durable ledger.** `app/ledger.py` keeps audit and idempotency keys
  under `STATE_DIR`, fsync'd; keys are derived per action and reserved
  BEFORE the call (the build-time constant is gone); a crash mid-call
  leaves a key that refuses to be retried blind. Governed tools take
  authority from the principal, enforce their declared input schema, and
  record redacted arguments with the request id.
- **A measured denial of service, fixed.** Perception's table detection
  backtracked quadratically: a 40KB body cost thirty seconds of CPU per
  request, unauthenticated. Replaced with a linear scan.
- **Retrieval.** Re-indexing no longer corrupts document frequencies;
  every hit carries its source document so recall@K grades per document;
  `evals/retrieval.py` measures the pipeline's wired retriever after the
  corpus loads; four templates that had no `run(payload)` gained one; the
  two Qdrant graph templates gained the class the pipeline instantiates
  (an emission choosing them failed at import before).
- **Reasoning answers from evidence.** The llm reasoning template calls
  the model with retrieved evidence framed as data — the discipline the
  harness already had, applied to the application — and refuses without
  a question.
- **Harness and eval gates.** Field-level breakdown for structured
  outputs; an empty adversarial set is red, like an empty golden set;
  `--report` JSON kept as a CI artifact; `evals/calibrate.py` and an
  UNCALIBRATED banner on every judged run until a human-agreement bar is
  met (a refused judge turns the run red); `JUDGE_ENDPOINT`/`JUDGE_MODEL`
  so the judge is not the author; judged evals on a build whose data may
  not leave run only on an `inside-boundary` runner; the case schema is
  documented.
- **Deploy.** The hardening set (Protect*, Restrict*, SystemCallFilter,
  capability bounding, Tasks/Memory/NOFILE limits, StateDirectory,
  StartLimit); releases side by side with a `current` symlink, so
  rollback is one atomic command and the runbook is finally true; a
  nologin service account; the package staged, not the working tree; the
  env file required. Ansible in parity.
- **Documents.** RISKS.md lists the unanswered assumptions and separates
  decided from implemented; the README's pieces and a run-it-locally
  section; the runbook's request-id claim is true; `env.example` covers
  every variable, the new ones included.
- **Supermemory** joins the registry (MIT, one local binary on 6767) as
  an episodic-store realization offered where the client already runs
  it; the hosted host is refused behind a boundary.
- Templates: governance's autonomy branch was unreachable and approval
  latency defaulted to thirty seconds (now checked, and measured);
  labelled-metrics scored truthiness (every class string is truthy, so
  two wrong decisions scored 100%) and now scores equality per class; OCR
  perception refuses without an engine and routes weak regions to a
  person; memory templates return the envelope.

Deferred, named: stateful component singletons under concurrent
requests (per-request instances next); the MCP tool boundary's audit
still in memory; three taxonomy sources the harness cannot reach; SHA-
pinned actions and hashed installs; re-running the public demos on this
emitter so what they show is what this emits.

## [0.1.16] — 2026-09-16

The fourth escalation on emitted-code quality pointed at the application
code itself, so the acceptance suite grew the checks that read every
emission the way a client's staff engineer does:

- **A real bug, fixed**: the emitted model seam's bounded retry called
  `time.sleep` without importing `time` — the retry path crashed with
  NameError on its first transport blip (shipped since 0.1.14; nothing
  exercised the path).
- **Emitted code is lint-clean, permanently**: every emission passes
  `ruff --select F,E,W,I,B,UP` as an acceptance check — an undefined
  name, an unsorted import block or a deprecated idiom is now a release
  blocker, which is what caught the bug above.
- **No passthrough padding**: emitting without a registry chained
  deployment/provisioning/evaluation as payload steps — and the
  acceptance suite itself was doing exactly that, blessing code no real
  build produces. Library callers now get the same payload-only
  pipeline `fde build` emits, the suite emits with the registry, and a
  check pins the property.
- **`run()` is no longer anonymous**: typed signature, and a failing
  step's name reaches the journal as structured JSON before the
  exception propagates unchanged — refusals pass through untouched.
- **Advisory components say so in their first lines**: a module that is
  decided-on-record but never chained carries the header (finding 20
  closed).
- The emitted smoke gains the promised deliverable invariants: unwired
  approval gates and critics fail closed, and rank fusion rewards
  agreement between retrievers.

## [0.1.15] — 2026-09-15

The bar became executable. Three escalations on emitted-code quality in a
row proved audit-and-patch is whack-a-mole, so this release changes the
mechanism: `tests/test_acceptance.py` emits projects across representative
architecture shapes and holds every emission to the operational contract —
permanently. Every future quality finding lands there as a check before it
lands anywhere as a fix. What the suite convicted on its first run, fixed
at the emitters:

- **The deliverable was uninstallable from its own box**: the systemd unit
  demanded `/opt/app/.venv`, user `app`, `/var/lib/app` and `/etc/app/env`
  while nothing shipped created any of them. The deploy README now carries
  the full install sequence derived from the unit itself, and the ansible
  playbook stages the whole package, builds the venv, creates the state
  dir and installs the env file (never overwriting an edited one).
- **A model-free CI lane**: emitted workflows gate every push on the
  deliverable's own smoke; a judged evaluation joins only where the
  repository configures `LLM_ENDPOINT` — a workflow that can never pass is
  a permanent red X teaching everyone to ignore CI.
- **The deliverable carries its own floor**: `tests/test_smoke.py` — the
  contract exists, the fence holds at import, the exam refuses to be
  empty. Model-free, seconds, true at emission and after implement.
- **The runbook opens with the first five minutes**: systemctl, journalctl,
  the health and readiness probes, and how a correlation id finds a
  request's log line — commands before doctrine.
- `env.example` documents `LLM_ENDPOINT` truthfully on no-model builds too
  (the /ready preflight reads it; unset is correct and now says so).

## [0.1.14] — 2026-09-14

The operational shell, from a staff-engineer acceptance review that
graded the emitted deliverables C-to-F on operations and refused to sign:

- **The service tells operators the truth**: structured JSON logs to
  stderr, flushed (journalctl showed literally nothing at 3am before);
  the unit sets PYTHONUNBUFFERED; SIGTERM flushes and exits clean;
  errors carry a correlation id.
- **Dependency failures are 503s, not mysteries**: a dead or stalled
  model endpoint answers with retry-later semantics; `/ready` runs a real
  preflight (model reachable, config present) so a deploy gates on it —
  `/health` stays honest liveness. Boot logs its preflight problems.
- **Configuration is one story**: the unit reads `/etc/app/env`
  (EnvironmentFile), a generated `deploy/env.example` documents every
  variable the emitted service actually reads — including the model
  variables exactly when the build needs a model — and STATE_DIR points
  writable state at /var/lib/app where the unit's sandbox allows it.
- The one model seam gets one bounded retry and an `LLM_TIMEOUT` env;
  the hosted path's `anthropic` import failure explains itself; emitted
  projects ship their own `.gitignore`; the interpreter floor matches
  what the deliverables actually run on (3.10).

Deferred to the next batch, tracked: a model-free CI lane for emitted
workflows, a complete ansible path, a unit-test smoke in the
deliverable, and a generated "first five minutes" runbook section.

## [0.1.13] — 2026-09-14

Two hostile audits before the framework's first Show HN — one attacking
the shipped code, one reviewing the emitted deliverables as a client's
staff engineer. Everything they broke, fixed at the emitters:

- **The judge parser can no longer be inverted by chatter**: "not
  correct" graded as a pass, "incorrect\ncorrect" passed on contradiction.
  Verdicts now read from the last line, negations and self-contradictions
  are ungradeable, and ungradeable fails visibly — pinned against the
  audit's exact replies.
- **The emitted service survives hostility**: threaded (one slow socket
  froze the whole service, /health included), read deadlines, a body-size
  cap, 400/404/411/413 for the parsing edges that dropped connections,
  and a 500 with the exception's name where any unexpected failure
  previously killed the socket silently — on a fresh build that was every
  POST. Binds loopback by default: exposure is a deployment decision,
  never a code default.
- **The ladder stops arguing with the tools above it**: a built
  engagement is never sent back to the interview; the implement hint uses
  the out-path build actually recorded; the ask hint carries the --scope
  that surfaces its question; a garbage LLM_ENDPOINT no longer clears the
  model rung.
- **Budgets are honest**: agent-round timeouts are labelled timeouts and
  visible even when files changed; --check-timeout joins --agent-timeout;
  non-positive budgets are refused.
- The prose reader matches phrases whitespace-flexibly on the original
  text (CRLF briefs included), keeping every span exact; the emitted
  llm.py caps tokens; the emitted package is named for its delivery, not
  "generated"; the load test's arrival default resolves at emit time.

## [0.1.12] — 2026-09-13

The corrected record, carried to every frozen surface:

- Status: three complete demonstrations, all public — including the third
  run's calibration gate refusing its own judge exactly as the prediction
  published beforehand said it would (73.7% agreement vs the 0.80 bar;
  the judge's 89.5% was 26 points of flattery over the hand-graded 63.2%),
  and 100% recall@10 on the retrieval eval's first real-data queries.
- `fde scan`'s extraction note tells the corrected receipts story — the
  0.6B extractor reached the exam's provable optimum; audit the exam
  before blaming the model.
- The Documentation table row an earlier edit corrupted is repaired, and
  all three demonstration repositories are linked from it.

## [0.1.11] — 2026-09-13

Found by asking the simplest question nobody had asked: has anyone
deployed the deliverable?

- The emitted deployment unit runs `python -m app.pipeline` — and the
  emitted pipeline defined functions and exited cleanly, a service that
  dies silently on its first start. The pipeline is now the service:
  stdlib-only HTTP, `/health` for the probe, POST `/` hands the JSON body
  to `run()`, and a contract refusal is a 422 with the reason — the
  fail-closed honesty, spoken over HTTP. Pinned by starting the emitted
  service and talking to it.
- `fde scan`'s extraction note tells the corrected receipts story: a 0.6B
  extractor reached a real exam's provable optimum — audit the exam
  before blaming the model.

## [0.1.10] — 2026-09-13

The model research becomes product:

- `fde next` knows the wall both demonstrations hit: a build that calls a
  model, with no `LLM_ENDPOINT` standing, gets "run `fde scan`" as its
  next move — which names the runtime, the model sized to the measured
  hardware, and the export line. Never silence at the exact step a user
  is stuck on.
- `fde scan` carries the measured doctrine: judging has a floor (sub-1B
  judges agree with human graders ~68%, 4B-class ~88% — verdicts, never
  scores, calibrate first), and schema-bound extraction is the one job a
  sub-1B model may honestly hold (a 0.6B extractor measured a 72.6%
  ceiling on noisy OCR), with specialist extractors as the staged
  upgrade.
- The site gains a dated, sourced local-models guidance page merging the
  published benchmarks with the first-party numbers from the public
  demonstration runs.

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
