# Security

## Reporting a vulnerability

Open a private report via GitHub's **Report a vulnerability** (Security →
Advisories) on this repository. Include what you found, how to reproduce it,
and what an attacker gains. You will get an acknowledgement within a week.

Please do not open a public issue for anything exploitable before it is
fixed.

## What counts as a vulnerability here

Beyond the usual (code execution, path traversal, injection), this project
treats two more things as security-grade, because the framework's promises
depend on them:

- **A bypass of the hard gate.** `data_access` is the one gate that cannot
  be waived. Any input — CLI, hand-edited state file, unicode trickery —
  that lets an engagement proceed past it without a verified attestation is
  a vulnerability, not a quirk.
- **A leak path for client material.** The sanitisation gate exists so that
  nothing identifying a client can be committed or published. Anything that
  writes outside its reach (path traversal in `kb ingest-case`, content
  that evades the tracked-path checks) is in scope.

Both classes have been found and fixed before; reports of either are taken
seriously.

## What this project does with your data

Nothing. The framework runs from plain files, makes no network calls, and
never transmits engagement content anywhere. Engagement directories,
research and supplied material are excluded from version control by
construction and enforced in CI.
