# Bring an engagement

The README's claim ladder ends on a rung that only engagements can move:
whether an engineer using this framework makes better decisions, sooner,
with less rework, than one without it. The first five engagements that run
to [`EXPERIMENT.md`](EXPERIMENT.md) are how that rung gets measured. This
page says what such an engagement is, what each side gives and gets, and
what is not on offer.

## The shape of it

One problem, brought by someone who owns the workflow it lives in, worked
to a scored build or a recorded stop. The shapes that have run end to end
in public are the ones that go fastest: extracting fields from documents,
routing or triaging free text into queues, deciding a label from labelled
history, answering questions from a document base. Two to four weeks each
on the record so far. A shape nothing here has served yet is welcome, and
slower, and the framework will say early if its registry cannot serve it.

## What you give

- **The problem as you would put it to a colleague**, three sentences. The
  framework reads it into typed facts and asks for what it still needs.
- **Real examples.** Inputs with the answers your people gave, a few
  hundred if you have them, forty at the least. They become the exam the
  build has to pass and a holdout the delivery never sees. Nothing leaves
  your environment; the exam runs where the system runs.
- **A baseline someone measured**: volume, time per item, hours, error and
  exception rates. Stated figures are accepted and marked as stated.
- **Someone who will sign an outcome contract**: which number this system
  exists to move, from what to what, measured how, by when. Nobody builds
  without one, or without a written reason it cannot be set yet.
- **Half an hour of interview time** from the people who own the data,
  the workflow and the judgement of what is good enough.
- **Your data boundary**, stated. Air-gapped, on-premise and your own
  cloud account are all served; a hosted model is used only where you say
  data may leave.

## What you get

- **An architecture decision with its receipts**: what was chosen, what
  was rejected and why, every decision traced to a fact and every fact to
  who said it. Plain code where plain code is enough; a model only where
  the evidence earns one.
- **A deployable project**: pipeline, evaluation harness, deployment
  assets for your environment, a runbook, the risks with the waivers named,
  and a scorecard of what the build can prove about itself out of sample.
- **A stop, if the evidence says stop.** A stop condition goes on the
  record before the build. If the numbers trigger it, the engagement stops
  and says why. That is a legitimate outcome, and it costs you less than a
  system that should not have been built.
- **The record**, which is yours: every gate, waiver, forecast, incident
  and outcome, readable by anyone who picks the engagement up after.
- **Handover**, not operation. Your platform team runs it; the runbook and
  the diagnosis walk are written for them.

## What the framework gets

One row in the experiment. That means: the engagement's record with the
figures in `EXPERIMENT.md`, an outside reviewer scoring the architecture
blind, and, if you agree, an anonymised case in the public corpus with
the numbers and none of the data. You choose the level: nothing public,
the figures only, or the case with your sector named. Your examples,
your documents and your people's words never enter the repository; that
is enforced by a test, not a promise.

## Cost

No charge for the first five engagements that run to the protocol. You
cover your own infrastructure. If the engagement goes beyond the protocol
into operation, integration work or a second system, that is separate
work at a rate agreed first.

## What is not on offer

- A guarantee of a build. The gates refuse until the evidence is there,
  and the stop condition is real.
- Production operation, on-call, or an SLA. The delivery includes the
  runbook and the SLO page; running it is your team's.
- Hosted models against your wish. The boundary is yours and the emitted
  service refuses to cross it.
- A benchmark claim. Five engagements are five rows. The report will say
  what its count can show and nothing more.

## How to start

Open an [engagement proposal](https://github.com/atulkapoor/fde-framework/issues/new?template=engagement.yml)
with the problem in three sentences, or run the first step yourself:

```bash
pip install fde-framework
fde triage --statement "The problem as you would put it to a colleague."
```

and send the output. Nothing in it is your data.

---

# Engagement agreement

Plain language, for the first five engagements. Have your own counsel read
it before anyone signs; it is a draft written by an engineer, not a lawyer.

**Parties.** The client, who owns the workflow and the data, and the
engineer, who works the engagement with the framework.

**Data.** The client's data, documents, examples and the words of its
people stay in the client's environment. The engineer works inside that
environment or on exports the client provides for the purpose, and
deletes any copy at handover. Nothing of the client's enters any public
repository; the framework's test suite refuses tracked client material,
and the engineer will show the client that check on request.

**Deliverables.** The emitted project and everything in it, the record of
the engagement, and the handover documents belong to the client on
delivery. The client may use, change and redistribute them without
restriction. The framework itself stays under its own licence.

**The record.** The engineer may keep the engagement's figures as defined
in `EXPERIMENT.md`, the blind review of the architecture, and a case
anonymised to the level the client chooses in writing: nothing public,
figures only, or a case naming the sector. The client may change that
level down at any time before publication and the engineer will comply.

**Outcome contract and stop.** The client names the owner, the metric,
its baseline and target, the method and the window before the build. The
stop conditions are agreed in writing before the build. A stop triggered
by the evidence ends the engagement without further obligation on either
side, and the record says why.

**Cost.** No fee for an engagement run to the protocol. The client bears
its own infrastructure and its people's time. Work outside the protocol
is agreed separately in writing before it starts.

**Warranty.** The deliverable is provided as it is measured: the
scorecard states what the build can prove and where it stops, and no
other fitness is warranted. The client decides whether to deploy it.

**Ending.** Either side may end the engagement in writing at any time.
The client keeps whatever has been delivered; the engineer keeps the
record to the agreed level and nothing else.

Signed, dated, by a person who can bind each side.
