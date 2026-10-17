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

1. **Find the tool.** With the `fde` MCP server configured you have the
   tools `triage`, `start`, `frame`, `status`, `next`, `stage`, `debt`,
   `stop_when`, `history`; use them. Otherwise the command line: `fde
   --version`. Done when you know which of the two you have -- or, with
   neither, when you have said the install line (`pip install
   fde-framework`; `pip install "fde-framework[mcp]"` for the server)
   and stopped there. Installing is the person's.

2. **Triage when there is more than one candidate.** `triage` compares:
   give it each problem as the person stated it, in their words (`fde
   triage --statement "..." --statement "..."`). It measures how much of
   the decision each statement already settles -- decidability, not
   value -- and says so itself. Done when the ranking is on screen as
   returned. With one problem, go to the next step.

3. **Open the engagement.** `start` (or `fde start <name> --statement
   "..."`) with a plain name; it writes to `engagements/<name>/` under
   the workspace. A brief, a spec, a thread, notes: put the text through
   `frame` (or `fde frame <name> --text "..."`), which turns it into
   typed facts, each marked with where it came from. Every fact in the
   record is the person's own words, through `frame`. Done when `start`
   has answered ok and every text the person gave you is framed.

4. **Ask for the next thing.** `next` (or `fde next <name>`) names one
   action and what turns on it. Relay it word for word. When the action
   is yours -- framing more text, reading a file they point at -- do it
   and ask again. When it is a person's -- measure a baseline, name an
   evaluation owner, show that data access works -- it is theirs: put
   the question to them in the framework's words and stop there. Done
   when the person holds the next action and knows it is theirs.

5. **Show where it stands.** `status` (or `fde status <name>`) is what is
   known, who said it, and which gates block the build; `debt` is what
   nobody has settled, with an owner; `stage` is where the engagement is
   on its record. Quote each as printed. Done when the person has read
   the framework's words, not a kinder version of them.

6. **The design, or the brief.** `fde architect <name>` prints the design
   with its reasons and what is undecided; `fde report <name>` writes one
   Markdown brief for a reader who is not at the terminal. Both read the
   record. Done when the file or the output is in the person's hands.

## Whose act each thing is

- **A build is the person's.** `fde build`, `fde implement`, and any
  command that writes a project or runs an agent happen at their
  terminal, after eight gates pass. When they ask you for one, name the
  command and hand it over: "that is `fde build acme --out project`,
  and it is yours to run."
- **An attestation is a signature.** A waiver (`fde waive`), data access,
  a security review, a deployment, a baseline: each is a statement a
  named person signs. Relay what the gate asks for and who owns it; the
  signing is theirs.
- **The record writes itself.** Everything under `engagements/` is
  written by the commands, append-only, every entry with its source.
  What you add goes in through `start` and `frame`.
- **A refusal is the answer.** "blocked by data_access" means the build
  waits for a connection that returned real rows. Carry that sentence to
  the person as it stands; it is the framework working.

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
