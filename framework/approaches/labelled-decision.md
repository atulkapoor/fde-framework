---
id: labelled-decision
name: Labelled decision from text
complexity: 1
components: [reasoning]
applies_when: [output_shape == decision and input_format == text]
avoid_when:
  - output_shape == decision and labelled_count >= 1000
  - input_format == documents
  - input_format == scanned_documents
evidence: {case_ids: [churn-scoring], confidence: medium, last_verified: 2026-09-18}
---
A decision read off a narrative -- a complaint, a ticket, a note -- with a
small labelled history: a few dozen to a few hundred pairs, too few to
learn a model from and too many to ignore. It is a classification wearing
a decision's name, and the corpus already knows that for the thousands
case; this is the same finding for the hundreds case, where a solver was
once handed a hundred and twenty complaints and had nothing to optimise.

Three things the emitted reasoner carries because the pairs carried them:
the label set as a contract (an answer outside it is a refusal, not a
creative decision); a runnable baseline fitted to the visible cases --
token log-odds per label, deterministic, no model -- that beats the
majority rate on day one and is measured against the holdout it never
saw; and a seam for a model-backed classifier behind the boundary, which
must name one of the labels or defer to the baseline.

Not for documents or scans: those are extraction problems first, and the
decision comes after the fields do. Above a thousand labels, the learned
model wins and this steps aside.
