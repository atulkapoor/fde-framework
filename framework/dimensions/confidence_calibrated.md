---
id: confidence_calibrated
type: boolean
scope: non_functional
kind: requirement
weight: 1.0
asks: "Has the cheap path's confidence been measured against known answers?"
ask_role: [eval_owner, admin]
recognises:
  "true":
    - confidence is calibrated
    - we measured the error rate
    - validated against ground truth
  "false":
    - never been calibrated
    - never calibrated
    - not calibrated
    - confidence is a guess
---
Whether a confidence score means anything.

The question decides if a cascade is available at all. Routing on an
uncalibrated score is a cost saving with an unknown error rate attached, and the
error rate is the part the client finds out about later.

Model confidence is typically miscalibrated, and asking a model how sure it is
performs substantially worse than probe- or perplexity-based measures at
predicting when it is actually wrong. A threshold calibrated on one workload
routinely fails on the next, so this is measured per engagement rather than
inherited.
