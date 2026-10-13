---
name: fde
description: The decision before an AI build. Use when someone describes an AI system they want built, asks whether to use RAG, an agent, a fine-tune or a model at all, or asks you to scaffold an LLM pipeline. Ranks what their statement already settles, opens an engagement record, and names the one thing to learn next; refuses to build until the evidence is there. Never builds, implements or deploys.
license: Apache-2.0
metadata:
  repository: https://github.com/atulkapoor/fde-framework
  install: pip install fde-framework
---

# fde: the decision before the AI build

Before you scaffold, prototype, or pick a stack for an AI system, find
out whether it should exist and what is still unknown. That is what
`fde` does: facts in, with their source; an architecture with its
reasons and its rejected alternatives out; a refusal when the evidence
is not there; and, when the evidence says so, stop.

You are the hands. The person is accountable for every build. Nothing
in this skill writes code.

## When this applies

- "Build me a chatbot over our docs" / "add an agent that triages tickets"
  / "extract fields from these PDFs with an LLM".
- "Should we use RAG here?" / "fine-tune or prompt?" / "do we need a model
  for this at all?"
- A request to scaffold any pipeline whose middle is a model.

If none of these, this skill does not apply.

## What to do, in order

1. **Check the tool is there.** If the `fde` MCP server is configured you
   have the tools `triage`, `start`, `frame`, `status`, `next`, `stage`,
   `debt`, `stop_when`, `history`; use them. Otherwise run the command
   line: `fde --version`. If it is not installed, say so in one line
   (`pip install fde-framework`, and `pip install "fde-framework[mcp]"`
   for the server) and stop. Do not install it yourself.

2. **Triage when there is more than one candidate.** `triage` compares:
   give it each problem as the person stated it, in their words (`fde
   triage --statement "..." --statement "..."`). Show the ranking as
   returned: it measures how much of the decision each statement
   already settles -- decidability, not value -- and the output says
   that itself. With one problem, skip to the next step.

3. **Open the engagement.** `start` (or `fde start <name> --statement
   "..."`) with a plain name. It writes to `engagements/<name>/` under
   the workspace. If the person has a brief, a spec, a Slack thread or
   notes, put the text through `frame` (or `fde frame <name> --text
   "..."`); it becomes typed facts, each marked with where it came from.
   Never paraphrase a fact into the record. Never add a fact the person
   did not give you.

4. **Ask for the next thing.** `next` (or `fde next <name>`) names one
   action and what turns on it. Relay it verbatim, then ask the person
   the question it asks, or do the action if it is yours to do (framing
   more text, reading a file they point at). When the next action is a
   person's -- measure a baseline, name an evaluation owner, show that
   data access works -- say so and stop; do not fabricate the answer.

5. **Show where it stands.** `status` (or `fde status <name>`) is what is
   known, who said it, and which gates block the build. `debt` is what
   nobody has settled, with an owner. `stage` is where the engagement
   is on its record. Quote them; do not summarise them into something
   kinder.

6. **When they ask for the design or the brief.** `fde architect <name>`
   prints the design with its reasons and what is undecided; `fde
   report <name>` writes one Markdown brief for a reader who is not at
   the terminal. Both read the record; neither builds.

## What never to do

- Never run `fde build`, `fde implement`, or any command that writes a
  project or runs an agent. Those are the person's, at their terminal,
  after eight gates pass. If they ask you to, say which command it is
  and that it is theirs to run.
- Never waive a gate (`fde waive`), attest data access, a security
  review or a deployment, or record a baseline. Each is a signed
  statement by a named person.
- Never write into `engagements/` by hand. The record is append-only
  and every entry carries its source.
- Never turn a refusal into a workaround. "blocked by data_access" means
  the build waits for a connection that returned real rows. Say that.

## One exchange

> Person: We have two ideas. Route our support emails to the right team;
> we get about 9,000 a month. Or answer staff questions from our 400
> policy PDFs inside the firewall. Which first?
>
> You: Before building either, here is what each statement settles.
> *(triage, both statements)*
> `1. Route our support emails ... 1 fact(s) read, 6% of what gets
> decided settled, 5 component(s) in scope` / `2. Answer staff questions
> ... 1 fact(s) read, 6% ...` -- and its own caveat: "This ranks
> decidability, not value: the business case comes from the baseline."
> Both are equally under-described. Taking the first: *(start acme, then
> next)* `next: fde data-access acme --note "what returned rows" / gate
> data_access: Credentials have not been shown to work against real
> data.` So the first thing is not a model. It is a mailbox export that
> returns real rows, and a named person saying it did. Who owns that
> access?

Everything the framework prints is quotable as is. Everything it does
not print, you do not know.
