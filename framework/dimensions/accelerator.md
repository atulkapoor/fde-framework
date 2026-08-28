---
id: accelerator
type: enum
scope: environment
kind: environment
weight: 1.0
asks: "What accelerator does the machine this runs on have?"
values: [none, single, multi]
recognises:
  none: [no gpu, cpu only, cpu-only, no accelerator, no cards]
  single: [one gpu, a single gpu, one card]
  multi: [several gpus, multiple gpus, a gpu node, eight cards, four cards]
ask_role: [admin]
---
Capacity class, not hardware. Three values because three things change: nothing
local, one device, or enough devices to split a model across.

Worth detecting rather than asking. An administrator's recollection of what is
in a rack is a statement with confidence attached; the machine knows, and a
measurement outranks a recollection in this framework by construction.

`none` does not rule out running locally -- a small quantised model on CPU is a
real answer, and the right one when nobody is waiting. It rules out running
locally *at interactive speed*, which is a different claim and the one that
matters.

`multi` is what makes a model larger than one device available at all. Below
that the levers are quantisation, then parameter-efficient adaptation, then a
smaller model -- in that order, stopping at the first that fits.
