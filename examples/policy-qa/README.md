# Worked example: policy Q&A over documents

A freeform-answer engagement, start to build, using the three files in this
directory. Everything below is a real transcript — a synthetic engagement
with made-up policies, in the shape of a common one: support engineers
asking questions over a large internal document base, inside a data
boundary.

What this example exercises that invoice extraction does not: a retrieval
layer with its own recall eval, a judged (model-graded) evaluation and the
offline-evaluability gate it triggers inside a boundary, and an honestly
undecided component.

```bash
fde start helpdesk --statement "Answer support engineers' policy questions from the document base."

fde frame helpdesk --file examples/policy-qa/brief.md
# Here is what I took from that:
#   - What does the system produce: freeform
#   - How many items in total: 40,000
#   - Where does this run: on prem
#   - Can client data leave their environment: cannot leave
#   - How many are verified or labelled: 300
#   - How many systems does this have to touch: 2
#   - Is a person waiting for the result: no
#   - What shape are the questions people ask: lookup

fde samples helpdesk --file examples/policy-qa/pairs.jsonl
fde status helpdesk
# blocked by 5 -- the usual four, plus offline_evaluability: freeform output
# needs a judge, and nothing may leave here. The remedy names the plan and
# the command.

fde baseline helpdesk --file examples/policy-qa/baseline.yaml
fde data-access helpdesk --note "document store returned 40,112 rows over the search API"
fde security-review helpdesk --note "client infosec reviewed retrieval paths and egress"
fde waive helpdesk client_readiness --reason "eval owner named, starts Monday"
fde waive helpdesk offline_evaluability --reason "local judge planned: qwen on Ollama, calibrated against the eval owner before any quoted number"

fde architect helpdesk
# topology on-prem   [f16fe0971e9983f3]
#   deployment       systemd-unit via plain-python
#   evaluation       judged via plain-python
#   governance       boundary-and-audit via plain-python
#   integration      governed-tools via plain-python
#   observability    traced via plain-python
#   provisioning     manual-runbook via plain-python
#   reasoning        llm via plain-python
#   representation   segmentation via plain-python
#   retrieval        keyword-search via plain-python
#   serving          self-hosted via plain-python
#
# not decided: perception

fde build helpdesk --out project
# evals: 2 golden, 0 edge, 2 adversarial
# next: fde implement project --holdout engagements/helpdesk/artifacts/holdout.jsonl
```

Three things worth noticing.

**The retrieval layer ships with its own exam.** `project/evals/retrieval.py`
measures recall@10/@50 against golden queries — no model in the loop —
and refuses an empty case set rather than passing it:

```bash
python project/evals/retrieval.py
# retrieval_cases.jsonl is empty -- nothing was measured, so nothing
# passed. Seed it with golden queries and the document ids a correct
# top-K must surface.
```

**`not decided: perception` is the framework refusing to invent.** Nobody
said what arrives — chat messages? emailed PDFs? — so the component ships
as a module that raises with the reason, and `ARCHITECTURE.md` lists the
open question. An assumption would have been quieter and wrong more
expensively.

**The waivers are in the client's copy.** Both ship in `project/RISKS.md`
with their reasons — including the judge-calibration plan the
offline-evaluability gate demanded. And `fde next helpdesk` names the best
next move at any point (here: the accelerator question, which decides what
the local judge can run on).
