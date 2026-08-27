---
id: in-dpdp
name: India (DPDP Act)
as_of: "2026-08"
presets:
  data_residency: cannot_leave
obligations:
  - id: consent-notice
    produce: >-
      A notice and consent record for personal data processed by the
      system, in English and the scheduled languages the client's users
      actually use -- itemised purpose, not a blanket grant.
    verify: Counsel confirms the notice shape against current DPDP rules.
  - id: erasure-path
    produce: >-
      A working deletion path honouring a data principal's erasure request,
      exercised before go-live, derived artifacts included. Where audit
      retention conflicts, record the resolution: erase the personal data,
      keep the event skeleton.
    verify: Run a deletion end to end in staging and file the evidence.
  - id: breach-notification
    produce: >-
      A runbook entry for breach notification to the Data Protection Board
      and affected data principals, with named owners. The window is set by
      rules that have moved before -- the entry carries its own as-of date.
    verify: Re-check the current notification window when the drill runs.
  - id: significant-fiduciary-check
    produce: >-
      A screening answer on whether the client is (or will be notified as) a
      Significant Data Fiduciary -- which adds a DPO in India, audits, and
      impact assessments to the delivery.
    verify: Client counsel answers this one; the framework only asks it early.
  - id: cross-border-check
    produce: >-
      If any component sends data outside India (a managed API is sending
      data), the record of which countries and under what standing --
      transfers are restricted by notification, and the list changes.
    verify: Check the current negative list before relying on any transfer.
---
The India pack. Presets residency to cannot-leave as the safe default;
a stated, counsel-cleared transfer outranks it like any stated fact.

Same discipline as every locale: produce-and-verify items with dates,
never legal advice, never a new dimension. The DPDP rules have moved since
enactment and will move again -- which is exactly why every item carries
its own verification note instead of a confident number.
