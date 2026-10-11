# How it got here

The README says what the framework is and what it can prove today. This
is the record of how it got there: the outside readings, what each one
found, and the release that answered it. Every finding below became a
check in the test suite before it became a fix, which is why the story
can be told without the code having moved on from it. Release by release
detail is in [`CHANGELOG.md`](CHANGELOG.md).

## The audit passes, and the releases that answered them

The first three demonstrations -- receipts, complaints, rfc-qa -- found
the emitter's limits before any outside reader did. Six of this framework's releases (0.1.6–0.1.11) shipped from what
these runs found -- and after five independent audit passes reshaped the
emitter (0.1.17–0.1.21), the complaints engagement was built and implemented
again on 0.1.21: green in round 2, holdout 76.7% against the original's
63.3%, the run committed beside the original for comparison. A sixth pass,
widened to the exam, the components and the fine-tuning path, signed off
the freeform shape with conditions and refused the decision shape for
reasons that were the generator's; 0.1.22 answered each as a check first.
A seventh pass found those checks holding and the shape-specific work
stopping short -- a mis-specified baseline, an in-sample exam, a training
recipe that trained unshuffled on a prompt it never served -- and 0.1.23
answered again the same way. 0.1.24 then ran the fine-tuning recipe for
real on a small base model: the adapter learned the house style on cases
it never saw, and the six defects that run exposed in the harness, the
serving path and the comparison are fixed and pinned. An eighth pass gave
the decision shape its first sign-off, with conditions, and 0.1.25 met
them: probes on typical cases, label phrases rather than words, a merge
path that trains, a comparison that says what it can claim. A ninth pass
read the first industry run and the scorecard that measured it, and found
the card measuring self-consistency rather than fitness; 0.1.27 gave it
fitness rows -- the generalisation gap, an external exam a memoriser cannot
pass, the engagement's own error-rate bar -- and gave the routed decision
an abstain path and a reason on every answer.

Eleven further readings, of the source and of the published package,
followed between 0.1.28 and 0.1.45: an engagement record that carries the
lifecycle past the build, decision debt, stop conditions, forecasts, a
sandbox for the coding agent, an experiment protocol, the framework
served inside a coding agent over MCP and then confined, tested as a
product and driven by a real client, a release workflow that installs the
published wheel before it writes the release page. Each is a dated entry
in the changelog with the finding it answered.

## What the suite holds every emission to

Emitted quality is a pinned property, not a promise: the framework's own
test suite emits projects across representative architecture shapes and
holds every emission to the operational contract — every environment
variable the code reads is documented, everything the systemd unit demands
is created by a shipped installer, CI has a lane that goes green without a
model, the smoke test passes on a fresh emission, the code is lint-clean,
the payload path composes end to end and refuses garbage at the door, a
caller cannot forge a result, a hostile document or a long query costs
milliseconds, the journal stays one JSON line per event under threads, an
error closes its connection, a bad corpus file is skipped and counted, the
boundary refuses an endpoint outside it, the ledger survives a restart and
a torn line, a stopword cannot cite a document and a one-document corpus
still answers, compaction cannot drop a live key, every eval entry point
honours the boundary, an oversized corpus refuses the boot with one line,
readiness degrades rather than denies on a stray file, and the service
carries a request id on every answer, a truncated query is never a silent
miss, two processes cannot both reserve one key, a decision read off
labelled text ships a fitted classifier that refuses to serve a constant,
refuses an exam that changed since the build, beats the majority on the
holdout and says which of its scores are in-sample, the exam's probes and
edges come from cases the baseline was not fitted on and each steering
probe says what it steers toward, an uncalibrated judge is red until asked
for by name, a fact learned from a person is marked asserted rather than
established, and a fine-tuning decision ships a recipe that trains on the
prompt it serves -- and the deliverable ships its own edge tests, which
its CI runs. Eight independent audit passes took it from "every request
500s" to a sign-off with conditions on the decision shape.
