---
id: sensitivity_present
type: boolean
scope: data
kind: requirement
weight: 1.0
asks: "Do the fields themselves contain personal or otherwise sensitive data?"
recognises:
  "true": [contains pii, personally identifiable, personal data in the fields, patient names, customer names and addresses]
  "false": [no pii, fully anonymised, already pseudonymised, synthetic data only]
ask_role: ['admin', 'eval_owner']
---
Field-level, where data_residency is engagement-level. Residency says whether
data may leave; this says which of it would hurt if it did -- and the two
cross: data free to leave with sensitive fields inside it is the case where
redaction earns a place in the pipeline, because what leaves can be the
record with the identifying fields masked rather than the record or nothing.

The sample pairs already vote here: `fde samples` marks identifier-shaped
fields on the contract and raises this fact when it finds them, so the
question often arrives at the interview pre-answered by the client's own
examples -- at artifact strength, with the field names attached.
