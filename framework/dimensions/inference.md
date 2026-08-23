---
id: inference
type: enum
kind: requirement
asks: "Where does the model run?"
values: [hosted-api, self-hosted]
recognises:
  self-hosted: [self-host, self hosted, our own gpus, run the model ourselves]
  hosted-api: [call an api, vendor model, hosted model]
prunes:
  self-hosted:
    embeddings: [managed]
ask_role: ['admin']
---
API or your own weights.

Not the same question as `hosting`. A customer VPC can still call out to a
vendor API, and self-hosting is possible in every topology given hardware. What
couples them is egress: where nothing may leave, nothing may be called.
