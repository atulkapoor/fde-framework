---
id: arrival_rate
type: count
scope: data
kind: requirement
weight: 1.0
asks: "How many requests arrive per day, in the busiest month?"
recognises_near:
  [requests, queries, calls, transactions, invocations, per day, a day, daily]
ask_role: ['admin', 'eval_owner']
---
Flow, where corpus_size is stock. A half-million-document archive served four
times a day and a four-thousand-document queue hit every minute size in
opposite directions, and only one of the two numbers was being asked for.

This is the number fleet sizing actually consumes -- `fde cost` reads it from
the engagement rather than asking again at the prompt -- and the one that
decides whether the cheap path's economics matter at all: a rules-first
cascade that saves a model call is saving it this many times a day.
