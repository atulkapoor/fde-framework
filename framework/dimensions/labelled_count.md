---
id: labelled_count
type: count
scope: data
kind: requirement
weight: 2.0
asks: "How many are verified or labelled?"
recognises_near: [verified, labelled, labeled, annotated, reviewed, confirmed, ground truth]
ask_role: ['eval_owner', 'admin']
---
The number that decides whether supervised approaches are on the table.

The gap between this and `corpus_size` is an asset rather than a shortfall:
unverified items cannot train a model but can be mined label-free into a
prioritised queue of what to have a human verify next.
