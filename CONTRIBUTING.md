# Contributing

This framework is built from real engagements. That is what makes it useful and
it is also the thing most likely to go wrong, so read the first section before
anything else.

---

## 1 · Client material never enters this repository

Not in a file, not in a test fixture, not in a commit message, not in an issue.

What you may contribute is the **pattern, re-expressed in your own words**. What
you may not contribute is the material it came from.

| Never | Instead |
|---|---|
| A client's documents, data, schemas or screenshots | A synthetic example with the same shape |
| Client, employer or individual names | "a regulated lender", "the sponsor" |
| Verbatim text from a proprietary document | The idea, in your words, from your understanding |
| Real account numbers, identifiers, endpoints, keys | Obviously fake values |
| A figure you are not free to publish | The method for deriving it, and how to re-derive |

A pattern is not confidential. *"Structured extraction across varied layouts,
correctness non-negotiable, most rows unverified"* describes hundreds of
engagements. The moment it becomes identifiable, it is your client's, not yours.

CI enforces the mechanical part of this — tracked paths, credential and personal
data patterns, and a denylist. **It cannot catch a paraphrase close enough to be
identifiable**, and no regex will. That part is your judgement, and it is the
reason this section is first.

If you are unsure whether something is publishable, it is not. Open an issue
describing the *shape* of what you want to contribute and we will work out how to
express it.

---

## 2 · Contributions enter against a contract

The registry under `framework/` is data. Adding a stack, pattern, approach,
ladder or case is a file — never a change to `src/`. If your contribution
requires editing the core, that is a signal the design is missing an abstraction:
say so in the issue rather than working around it.

Each entry type has a schema in [`src/fde/models/schema.py`](src/fde/models/schema.py)
and each validator exists because of a specific way engagements go wrong.

**A pattern** needs realizations that all satisfy the same interface — otherwise
swapping the library silently changes the architecture rather than just the code
— and must include a `plain-python` realization. That last rule is not
bureaucracy: it is what lets the framework recommend *no library at all*, which
is frequently correct and never happens if the option does not exist.

**An approach** must state `avoid_when`. One that always applies has not been
thought about. If you cannot name where your approach loses, you do not yet
understand it well enough to contribute it.

**A ladder rung** needs `graduate_when`, and it must be measurable. "When the
team is ready" is not a trigger. Without it the framework defaults to the most
sophisticated rung, which is the exact failure ladders exist to prevent.

**A stack** declares its licence, the topologies it can run in, when it was last
verified, and how expensive it is to swap out. Reversibility is not the same axis
as cost: a reranker drops in without touching the index, an embedding model means
reindexing everything, and data sent to a third party cannot be un-sent at all.

**Evidence** is a pointer to a case, a date, and — for anything numeric — a
re-derivation rule. A rule with no evidence is a preference. Preferences are
welcome in discussion and not in the registry.

---

## 3 · How to work

Tests first. Every behaviour in this repo was written as a failing test before it
was implemented, and the tests read as statements about engagements rather than
about code — `test_a_disagreed_dimension_is_left_unresolved` rather than
`test_profile_returns_none`.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/ruff check src tests
```

Both must pass, plus `.venv/bin/fde kb validate --root framework` if you touched
the registry.

Commit messages explain **why**, not what — the diff already says what. Say what
would go wrong without the change.

---

## 4 · What is most useful

**Cases.** The corpus is the asset. A sanitised engagement — profile, decisions,
which graduation triggers fired and whether that was predicted, and the outcome —
is worth more than a feature, and contradictory cases are worth more than
consistent ones. Two engagements reaching opposite conclusions teach the
framework which dimension discriminates.

**Evidence against existing rules.** A rule that was wrong on your engagement is
more valuable than a new rule. Say what it recommended, what you did instead, and
what happened.

**Realizations for stacks that exist but have none.** A pattern with two
realizations is a pattern with a blind spot.

**Gaps.** Run `fde kb gaps`. Everything it reports is a real piece of work.

---

## 5 · Attribution

Commits are authored by the person who wrote them. Do not add co-author trailers
for tools, and do not attribute work to an AI assistant — CI checks this across
author, committer and message.
