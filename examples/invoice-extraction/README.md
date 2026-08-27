# Worked example: supplier invoice extraction

A complete engagement, start to build, using the three files in this
directory. Everything below is a real transcript — synthetic client, real
commands, real output.

The shape: 200k scanned documents, structured records out, on-prem with data
that cannot leave, 8,000 labelled examples, a person waiting on each answer.

```bash
fde start acme --statement "Extract structured fields from scanned supplier invoices."

fde frame engagements/acme --file examples/supplier-statements/brief.md
# Here is what I took from that:
#   - How many items in total: 200,000
#   - What arrives, and in what form: scanned documents
#   - Where does this run: on prem
#   - Can client data leave their environment: cannot leave
#   - How many are verified or labelled: 8,000

fde samples engagements/acme --file examples/supplier-statements/pairs.jsonl
# 3 pairs, 1 fields — the pairs settle the output shape and seed the golden set

fde status engagements/acme
# blocked by 3: [hard] data_access, baseline_capture, client_readiness
# build refuses until these clear -- the hard one has no waiver

fde baseline engagements/acme --file examples/supplier-statements/baseline.yaml
fde data-access engagements/acme --note "read replica returned 14 rows from the statements table"
fde waive engagements/acme client_readiness --reason "eval owner named, starts Monday"

fde architect engagements/acme
# topology on-prem   [7945b0e92edcc26d]
#   deployment       systemd-unit via plain-python
#   evaluation       field-match via plain-python
#   governance       boundary-and-audit via plain-python
#   observability    structured-logs via plain-python
#   perception       ocr-pipeline via plain-python
#   provisioning     manual-runbook via plain-python
#   representation   deterministic via plain-python

fde build engagements/acme --out project
# wrote project
```

The emitted `project/` holds `app/` (pipeline in topological order, boundary
check imported at startup because data cannot leave), `evals/` (golden set
from the three pairs, a harness that fails CI until the pipeline is
implemented), `deploy/` (a systemd unit — rung zero, because nothing in the
profile earned a container), `ops/` (runbook, SLOs, rollback),
`ARCHITECTURE.md` with every rejected alternative, and `RISKS.md` recording
the one waived gate and its reason.

Things worth trying from here:

```bash
fde ask engagements/acme --role eval_owner        # what's still worth asking
fde override engagements/acme --component representation \
    --choose llm-extraction --because "coverage measured at 60%"
fde retro engagements/acme --outcome "delivered" --days 18
```

Notice what the decisions did *not* do: no vector database for a lookup
workload, no Kubernetes for a single service, no LLM in the extraction path
while the deterministic mapper's coverage is unmeasured. The fingerprint
`7945b0e92edcc26d` is stable — rebuild from the same facts and the diff is
empty.
