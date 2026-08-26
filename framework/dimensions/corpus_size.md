---
id: corpus_size
type: count
kind: requirement
weight: 1.5
asks: "How many items in total?"
recognises_near:
  [documents, docs, document, files, records, pages, rows, accounts, items, tickets]
ask_role: ['admin', 'eval_owner']
---
Total volume. Distinct from how many are labelled, which is usually far smaller
and is the number that decides whether fine-tuning is available.
