---
id: licence_posture
type: enum
kind: requirement
weight: 1.5
asks: "Will the delivered system be shipped as proprietary software, used internally, or open-sourced?"
values: [proprietary, internal_only, open]
recognises:
  proprietary: [ships proprietary, closed source, closed-source product, sell the software, commercial product]
  internal_only: [internal use only, internal tool, never distributed, in-house only]
  open: [open source, open-source, will be open sourced, permissively licensed]
ask_role: [sponsor, admin]
---
What the client intends to do with the delivered system, because that is what
decides which component licences are usable.

Copyleft obliges publishing changes on distribution: fatal to a proprietary
product, usually irrelevant to an internal tool, immaterial to an open one.
Network copyleft (the AGPL class) triggers on *serving*, so even internal-only
can be exposed. The licence-compatibility gate crosses this answer with the
licences the chosen stacks actually carry, at build time -- the combination is
what bites, and no single component declaration can see it.

Asked of the sponsor because it is a business decision wearing a legal
costume, and discovered like everything else rather than assumed: a
consultancy that assumes "internal" hands its client a lawsuit the day the
product ships.
