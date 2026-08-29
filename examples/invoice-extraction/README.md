# Worked example: invoice extraction

A complete engagement, start to build, using the three files in this
directory. Everything below is a real transcript — a synthetic engagement
whose shape is assembled from publicly documented production deployments
(high-volume structured document extraction under a data boundary), with
made-up numbers on made-up invoices.

The shape: 500k scanned documents, structured records out, on-prem with data
that cannot leave, 10,000 labelled examples, a person waiting on each answer.

```bash
fde start acme --statement "Extract structured fields from scanned supplier invoices."

fde frame engagements/acme --file examples/invoice-extraction/brief.md
# Here is what I took from that:
#   - How many items in total: 500,000
#   - What arrives, and in what form: scanned documents
#   - What does the system produce: structured
#   - Where does this run: on prem
#   - Can client data leave their environment: cannot leave
#   - How many are verified or labelled: 10,000
#   - How many systems does this have to touch: 3
#   - Is a person waiting for the result: yes

fde samples engagements/acme --file examples/invoice-extraction/pairs.jsonl
# 3 pairs, 2 fields — the pairs settle the output shape and seed the golden set

fde status engagements/acme
# blocked by 4: [hard] data_access, baseline_capture, client_readiness, security_review
# build refuses until these clear -- the hard one has no waiver

fde baseline engagements/acme --file examples/invoice-extraction/baseline.yaml
fde data-access engagements/acme --note "read replica returned 14 rows from the invoices table"
fde security-review engagements/acme --note "client infosec reviewed data paths and egress"
fde waive engagements/acme client_readiness --reason "eval owner named, starts Monday"

fde architect engagements/acme
# topology on-prem   [82d56c303de52199]
#   deployment       systemd-unit via plain-python
#   evaluation       field-match via plain-python
#   governance       boundary-and-audit via plain-python
#   integration      governed-tools via plain-python
#   observability    traced via plain-python
#   perception       ocr-pipeline via plain-python
#   provisioning     manual-runbook via plain-python
#   representation   deterministic via plain-python

fde build engagements/acme --out project
# wrote project
```

The emitted `project/` holds `app/` (pipeline in topological order, boundary
check imported at startup because data cannot leave), `evals/` (golden set
from the three pairs, a harness that fails CI until the pipeline is
implemented, and `acceptance.md` — a blind-judging protocol for the client's
own people), `deploy/` (a systemd unit — rung zero, because nothing in the
profile earned a container), `ops/` (runbook, SLOs, rollback),
`ARCHITECTURE.md` with the scope read-out, the tools table with
in-topology alternatives, the agent posture, and every rejected
alternative, and `RISKS.md` recording the one waived gate and its reason.

Things worth trying from here:

```bash
fde ask engagements/acme --role eval_owner        # what's still worth asking
fde locale engagements/acme eu-gdpr               # jurisdiction obligations into the build
fde override engagements/acme --component representation \
    --choose llm-extraction --because "coverage measured at 60%"
fde retro engagements/acme --outcome "delivered" --days 18
```

Notice what the decisions did *not* do: no vector database for a lookup
workload, no Kubernetes for a single service, no LLM in the extraction path
while the deterministic mapper's coverage is unmeasured. The fingerprint
`82d56c303de52199` is stable — rebuild from the same facts and the diff is
empty. (The corpus evolves, and a corpus change that moves a decision moves
this fingerprint with it; the transcript above is re-run against the corpus
it ships with.)
