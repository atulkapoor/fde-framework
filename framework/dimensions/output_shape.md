---
id: output_shape
type: enum
scope: functional
kind: requirement
weight: 3.0
needs_judge: [freeform]
asks: "What does the system produce?"
ask_role: [eval_owner, sponsor, user]
values: [structured, freeform, classification, ranking, decision]
recognises:
  structured: [unified json, structured output, into a schema, extract fields, extract financial,
               populate fields, into json, structured records, structured data out]
  freeform: [draft a, write a summary, generate copy, answer questions, generate promotional,
             generate imagery, generate images, in our house style, freeform, free-form,
             prose output, open-ended answers, generate descriptions]
  classification: [predict which, classify, score each, will churn, risk score,
                   classification output, classification model]
  ranking: [rank, prioritise, order by relevance, shortlist]
  decision: [decide whether, choose an action, schedule, allocate, route to,
             output is a decision, decision output, assignments]
---
What comes out decides more than what goes in.

It selects the metric -- structured output is scored field by field, freeform is
judged, classification is scored against labels -- and it decides which
components exist at all. A classifier needs representation and a model; it does
not need a reasoning loop, and including one because there happened to be a
corpus is how an LLM ends up in front of a problem that never needed it.
