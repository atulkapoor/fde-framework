# Worked example: complaint triage that acts

A decision engagement, start to build, using the three files in this
directory. Everything below is a real transcript — a synthetic engagement
with made-up complaints, in the shape of a common one: every incoming
complaint gets a decision (refund, escalate, reply with an explanation)
that must reach three external systems.

What this example exercises: the agent posture. A system that acts on the
world gets a governed tool boundary, approval gates and critics in front
of anything irreversible, and an idempotency key so re-running cannot act
twice — decided from the facts, not bolted on.

```bash
fde start triage --statement "Decide each incoming customer complaint: refund, escalate, or reply with an explanation."

fde frame triage --file examples/support-triage/brief.md
# Here is what I took from that:
#   - How many systems does this have to touch: 3
#   - How many items in total: 5,000
#   - What arrives, and in what form: text
#   - Where does this run: customer vpc
#   - Can client data leave their environment: may leave
#   - Is a person waiting for the result: no

fde samples triage --file examples/support-triage/pairs.jsonl
fde baseline triage --file examples/support-triage/baseline.yaml
fde data-access triage --note "CRM replica returned 5,214 labelled complaints"
fde security-review triage --note "client infosec reviewed tool scopes and egress"
fde waive triage client_readiness --reason "triage lead named as eval owner, confirms Thursday"

fde architect triage
# topology customer-vpc   [86235323d95a908d]
#   deployment       systemd-unit via plain-python
#   evaluation       labelled-metrics via plain-python
#   governance       audit-only via plain-python
#   integration      governed-tools via plain-python
#   observability    traced via plain-python
#   perception       text-extraction via plain-python
#   planning         optimisation via plain-python
#   provisioning     manual-runbook via plain-python
#   reasoning        optimisation-reasoning via plain-python
#   representation   deterministic via plain-python

fde build triage --out project
# wrote project
# evals: 2 golden, 0 edge, 2 adversarial
# next: fde implement project --holdout engagements/triage/artifacts/holdout.jsonl
```

Two things worth noticing.

**The fashionable planner lost, on the record.** This is the "agentic"
shape — decisions, tools, three external systems — and the decision log
still reads:

```
**planning**
- `fixed-sequence` -- ruled out by output_shape == decision
- `model-planner` -- optimisation is simpler and applies here
```

A model-driven planner is in the corpus (with a LangGraph realization
ready), and it is reachable — when the facts demand it, or by
`fde override` with a measured reason. It is not the default just because
the workload says "agent". That is the whole doctrine in one rejection.

**The agent posture is decided, not configured.** `ARCHITECTURE.md`'s
posture section for this build:

```
- `integration` acts on the world. In front of it: approve-integration,
  critic-integration; idempotency key `1224ad29445b9354` so re-running
  cannot act twice.
```

Every outward call passes one governed boundary, anything irreversible
sits behind an approval gate and a critic, and the audit trail is what
`fde retro` later measures against the labelled decisions.
