---
id: eu-gdpr
name: European Union (GDPR)
as_of: "2026-08"
presets:
  data_residency: cannot_leave
obligations:
  - id: records-of-processing
    produce: >-
      A record of processing activities for the system: what personal data it
      touches, why, for how long, and who it is shared with (Article 30
      shape). The fact log and ARCHITECTURE.md carry most of the raw
      material; the record itself is a document the client's DPO signs.
    verify: Confirm with the client's DPO whether they are above the Article 30 thresholds.
  - id: erasure-path
    produce: >-
      A working deletion path for a data subject's records, exercised at
      least once before go-live -- including derived artifacts (embeddings
      are recoverable to their source and count as the data). Where the
      audit trail must be retained, record the resolution of the tension:
      erase the personal data, keep the event skeleton.
    verify: Run a deletion end to end in staging and file the evidence.
  - id: lawful-basis
    produce: >-
      A named lawful basis for each processing purpose, recorded beside the
      baseline. "We need it for the product" is a motivation, not a basis.
    verify: Counsel signs the basis per purpose.
  - id: breach-window
    produce: >-
      A runbook entry for the 72-hour breach notification window: who
      decides notifiability, who notifies the supervisory authority, and
      where the clock starts. The ops runbook carries the entry; the names
      must be real people.
    verify: Names and escalation tested in a drill, not just written down.
  - id: dpia-check
    produce: >-
      A screening answer on whether this processing needs a Data Protection
      Impact Assessment (large-scale, systematic, sensitive categories). If
      yes, the DPIA is a deliverable before go-live.
    verify: Screening documented even when the answer is no.
---
The EU pack. Presets residency to cannot-leave as the safe default -- a
stated architecture with a lawful transfer mechanism outranks it, exactly
like any other stated fact outranks an inference.

Obligations are produce-and-verify items, not legal advice: this file
cannot know the engagement's purposes or the client's counsel's view, and
pretending otherwise would be the framework guessing about law. What it
knows is the shape of what GDPR engagements are always asked to show, and
that arriving with the checklist beats discovering it in procurement
review.
