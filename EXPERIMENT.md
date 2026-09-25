# The experiment

Every claim the README marks *unverified* comes down to one question:
does an engineer using this framework make better decisions, sooner, with
less rework, than the same engineer without it? Nothing in the repository
can answer that. Engagements can, if they are run to a protocol written
before they start and followed by the record rather than by memory. This
is that protocol, and `fde experiment` is the part of it the framework
runs. It is small enough to start at five engagements and honest enough
that five will not prove anything; it says what five can show and what
only more can.

## The unit

One engagement is one problem brought by one client (or one client-shaped
owner who will sign an outcome contract), worked by one engineer, to a
scored build or a recorded stop. Ten to twenty engagements are the target;
five is the floor below which the numbers describe the engagements, not
the framework.

## The two arms, and how an engagement gets one

**With.** The engineer works the engagement through the framework from
`fde start` to `fde scorecard`, and on to `fde deployed`, `fde drift` and
`fde outcome` where the engagement gets that far. Every gate, waiver,
forecast and stop condition is on the record.

**Without.** The same engineer, or one of matched experience, works an
engagement of the same shape with their ordinary tools and process, and
keeps the control log: `fde experiment <eng> start` writes its template
into the engagement, with the same fields the framework's record supplies,
and the engineer fills it as the work happens, never afterwards. A field
left empty is reported missing; it is never estimated.

**Assignment is not a choice.** `fde experiment <eng> start` assigns the
arm: the lesser arm when the shape's counts differ, a draw seeded from the
series when they are equal. The draw and its seed are on the record.
Forcing an arm (`--arm`) is allowed and recorded as "by hand", and a
series with many forced arms is a weaker series. Pairing is by shape, not
by problem: the same problem cannot be worked twice by the same person
without the second run knowing the first.

**Order is recorded** because an engineer learns. The series numbers every
engagement in the order it started, and the report keeps that number
beside each pair, so a run of *with* engagements late in the series can
be seen for what it might be.

## What is frozen before anything is built

`start` freezes, with a timestamp, what the record held before the first
line of implementation: the forecasts on record, the outcome contract,
the stop conditions, and a difficulty vector read off the profile --
output shape, input format, labelled count, corpus size, external
systems, hosting, data residency, whether a person waits, whether
sensitive data is present, the arrival rate, which roles were heard, how
many facts were recorded, and whether the baseline was measured or
stated. An engagement started after a build already existed is marked so
and the report says it.

In the *without* arm the engineer writes the same things into the log,
in this order, before building: the statement as the client put it; the
evidence in hand, each item marked measured, stated or assumed; the
outcome contract; the architecture decision with the alternatives
rejected and why; forecasts with a confidence; what would stop the
engagement.

## The primary endpoint, declared now

The primary endpoint is **blind-review architecture quality**: the mean
of the six scores on the reviewer's form below. It is declared here,
before any engagement has been reviewed, so that no composite can be
assembled after the numbers are in. Everything else measured is
secondary and is reported beside it, never folded into it.

## What is measured

`fde experiment <eng> close` reads every figure below off the record in
the *with* arm and off the log in the *without* arm, and lists what is
missing for that engagement.

**Decision quality.** Architecture reversals after the first build;
approaches rejected that later proved right and approaches chosen that
later failed, as judged by the blind reviewer; requirements the client
stated after the first build that changed it; security or compliance
findings raised after the design was set; model use and infrastructure
the reviewer judges unnecessary.

**Speed and effort.** Days from start to a scoped statement, to an
architecture, to a first runnable build, to a green exam, to a pilot;
engineer hours from the timesheet, which the *with* arm must also
record by hand; implementation rounds to green; questions asked of the
client, and how many changed the design.

**Fitness.** Holdout accuracy and coverage on a holdout the engineer
never saw, drawn by the same rule in both arms; an external exam where
the client can supply a later export; the generalisation gap; forecast
errors, signed, per figure, and the held rate against the mean
confidence once five or more judged forecasts carry one.

**Outcome**, where the engagement reaches the field: the contracted
metric against its baseline and target, in its window; adoption;
incidents; whether the engagement was stopped, and by what.

## The blind review, and whether it is blind

`fde experiment <eng> packet` renders one packet in the same plain form
for both arms: the problem, the evidence in hand with its basis, the
outcome contract, the architecture with what was rejected and why, and
the fitness figures. Nothing in it names the arm. An independent
reviewer who has not seen either arm's work scores it on a fixed form,
`fde experiment <eng> review`, each from 1 to 5:

- evidence sufficiency: did the evidence in hand justify a decision at all;
- necessity: was what was built needed, or would something simpler have
  served;
- operational complexity, implementation complexity, risk, and
  reversibility, each judged apart, so "not the simplest" can say which
  way it was not.

The reviewer also says whether they would sign the outcome contract as
its owner, what they would have asked the client that nobody did, and --
separately, and required -- which arm they think produced the packet:
*with*, *without*, or *uncertain*. The report sets the guesses against
the truth. A reviewer who is right more often than a coin is not blind,
and the packet form has to change before the scores mean anything.

## What a count can and cannot show

`fde experiment <series> report` names the rung the count has reached:

- under five: descriptive only; the numbers describe these engagements,
  not the framework;
- five to nine: paired and exploratory; reversals, stops and forecast
  errors can be compared pair by pair;
- ten to nineteen: exploratory and worth reporting, with the spread;
- twenty and above: stronger, and still observational unless assignment
  was controlled throughout.

At no size does this protocol establish that the framework caused a
business outcome; that needs a comparison window on the same client
with the same people, which is a different experiment and a later one.
Nor does any average across shapes mean anything: the report pairs
within a shape and never averages across.

## What the framework supplies, and what people do

`fde experiment` runs the protocol on the record: `start`, `close`,
`packet`, `review`, `report`, and `template` for the control log.
`fde outcomes`, `fde bench`, `fde predict` and `fde history` read the
same record in other cuts. `fde retro` captures the engagement as a
case for the corpus after the window closes. Choosing the engagements,
keeping the control log honestly, finding a reviewer who has seen
neither arm, and running the field comparison are done by people, and
the framework does not pretend otherwise.
