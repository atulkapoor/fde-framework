# The experiment

Every claim the README marks *unverified* comes down to one question:
does an engineer using this framework make better decisions, sooner, with
less rework, than the same engineer without it? Nothing in the repository
can answer that. Engagements can, if they are run to a protocol written
before they start. This is that protocol. It is deliberately small enough
to run at five engagements and honest enough that five will not prove
anything; it says what five can show and what only more can.

## The unit

One engagement is one problem brought by one client (or one client-shaped
owner who will sign an outcome contract), worked by one engineer, to a
scored build or a recorded stop. Ten to twenty engagements are the target;
five is the floor below which the numbers describe the engagements, not
the framework.

## The two arms

**With.** The engineer works the engagement through the framework from
`fde start` to `fde scorecard`, and on to `fde deployed`, `fde drift` and
`fde outcome` where the engagement gets that far. Every gate, waiver,
forecast and stop condition is on the record.

**Without.** The same engineer, or one of matched experience, works an
engagement of the same shape with their ordinary tools and process, and
keeps a plain log: dated entries for every decision, every reversal, every
question asked of the client, every evaluation run, and the final figures.
The log is the control's record; it must be kept as it happens, not
reconstructed.

Pairing by shape, not by problem: the same problem cannot be worked twice
by the same person without the second run knowing the first. A shape is
the framework's own notion (extraction, a labelled decision, freeform
answering, routing, and so on), and each arm should carry the same mix.

## What is recorded before anything is built

In the *with* arm the record already forces this; in the *without* arm the
engineer writes the same things into the log, in this order, before the
first line of implementation:

1. the problem statement, as the client put it;
2. the evidence in hand, each item marked measured, stated or assumed;
3. the outcome contract: owner, metric, baseline, target, method, window;
4. the architecture decision, with the alternatives rejected and why;
5. forecasts, with confidence: the expected holdout accuracy, coverage,
   rounds to green, and whether any waiver will be needed;
6. what would stop the engagement.

A forecast written after its number exists is marked so in the *with* arm
by the framework and must be marked so by hand in the *without* arm.

## What is measured

Every figure below comes off the record in the *with* arm and off the log
in the *without* arm. A figure that one arm cannot supply is reported as
missing for that arm, never estimated.

**Decision quality**

- architecture reversals after the first build;
- approaches rejected that later proved right, and approaches chosen that
  later failed, as judged by the blind reviewer below;
- requirements found late: anything the client stated after the first
  build that changed it;
- security or compliance findings raised after the design was set;
- model use the blind reviewer judges unnecessary, and infrastructure the
  reviewer judges unnecessary.

**Speed and effort**

- days from start to a scoped statement, to an architecture, to a first
  runnable build, to a green exam, to a pilot;
- engineer hours, from the timesheet, not from memory;
- implementation rounds to green, and rounds spent red;
- questions asked of the client, and how many changed the design.

**Fitness**

- holdout accuracy and coverage on a holdout the engineer never saw, drawn
  by the same rule in both arms (`fde samples` draws it in the *with* arm;
  the *without* arm draws it by the same seed rule before building);
- an external exam where the client can supply a later export;
- the generalisation gap;
- forecast errors, signed, per figure, and the held rate against the mean
  confidence once there are enough to say anything.

**Outcome**, where the engagement reaches the field

- the contracted metric against its baseline and target, in its window;
- adoption; incidents; whether the engagement was stopped, and by what.

## The blind review

An independent reviewer, who has not seen either arm's work, receives for
each engagement: the problem statement, the evidence list, the outcome
contract, the architecture with its rejected alternatives, and the fitness
figures. Nothing in the packet says which arm produced it; the *with*
arm's documents are re-rendered into the same plain form as the *without*
arm's log before review. The reviewer scores, on a fixed form:

- was the architecture the simplest that the evidence justified;
- was anything chosen that the evidence did not justify, and anything
  rejected that it did;
- is the outcome contract one the reviewer would sign as the owner;
- what the reviewer would have asked the client that nobody did.

The reviewer's form is on the record beside the engagement.

## What five engagements can and cannot show

Five paired engagements can show whether the *with* arm produced a stop
or a reversal the *without* arm did not, whether its forecasts were
closer, and whether its packets scored differently under blind review.
They cannot show a difference in speed or fitness beyond noise, and no
average across five shapes should be quoted. At ten to twenty, signed
differences on the same figure across pairs become worth reporting with
their spread. At no size does this protocol establish that the framework
caused a business outcome; that needs a comparison window on the same
client with the same people, which is a different experiment and a later
one.

## What the framework supplies

`fde outcomes` prints the transitions, days to pilot, rounds, reversals
and incidents off a record; `fde bench` sets several records side by
side; `fde predict` scores the forecasts; `fde history` renders the whole
record as a dated log in the same shape the *without* arm keeps by hand.
`fde retro` captures the engagement as a case for the corpus after the
window closes. Everything else in this protocol is done by people, and
the framework does not pretend otherwise.
