"""What somebody needs at three in the morning, and what CI needs at merge.

A runbook that describes the architecture is not a runbook. What is wanted is:
here is what you will see, here is what it means, here is what to do -- and the
error taxonomy already classifies failures by source, which is exactly the
structure that answers it.

The rollback document is where this is easiest to get wrong. "Revert the
deployment" is a lie if the system sent anything, charged anything or wrote
anything downstream, so what rolling back does *not* undo is written out beside
what it does.
"""

from __future__ import annotations

from pathlib import Path

from fde.models.schema import earliest_cap

# What a failure of each kind looks like from outside, and what to do about it.
# Keyed on the taxonomy the evaluation harness already emits, so a classified
# failure leads somewhere rather than sitting in a report.
SYMPTOMS = {
    "data": (
        "Fields are missing or empty for a whole class of records, and the same "
        "records look wrong in the source too.",
        "The source was wrong before this system saw it. Check the feed, not the "
        "pipeline -- fixing this downstream means inventing values, which is worse "
        "than reporting the gap.",
    ),
    "input": (
        "Answers are wrong in a way that correlates with a document layout or a "
        "file type, and the extracted text looks mangled.",
        "Parsing lost it. Look at what perception reported it could not keep -- "
        "the clean share and the flattened tables. Nothing downstream recovers "
        "information that was never read.",
    ),
    "prediction": (
        "The value is present, plausible and wrong. Structure is fine; content "
        "is not.",
        "The rule or model produced it. Check the error breakdown by field: a "
        "single field dominating means a mapping to fix, spread failures mean a "
        "capability limit.",
    ),
    "output": (
        "Right values in the wrong shape -- a number as a string, a date in the "
        "wrong format, a field in the wrong place.",
        "The contract is being violated at the edge. Validate against the "
        "contract before returning rather than after somebody complains.",
    ),
    "system": (
        "Timeouts, restarts, memory exhaustion. Failures cluster in time rather "
        "than by input.",
        "Infrastructure, not logic. Check resource limits, concurrency settings "
        "and whether a dependency is degraded. Re-running the same input will "
        "usually succeed, which is how you tell.",
    ),
    "integration": (
        "Each component behaves correctly in isolation and the whole produces "
        "nonsense.",
        "The seam between two parts. Check the contract at the boundary -- shapes "
        "that almost match are the usual cause, and both sides look right when "
        "read alone.",
    ),
}


def write_ops(architecture, out: Path, registry=None) -> None:
    ops = out / "ops"
    ops.mkdir(parents=True, exist_ok=True)

    (ops / "runbook.md").write_text(_runbook(architecture, registry))
    (ops / "slo.md").write_text(_slo(architecture))
    (ops / "rollback.md").write_text(_rollback(architecture))
    _ci(architecture, out)


# --- runbook -------------------------------------------------------------


def _runbook(architecture, registry) -> str:
    components = sorted(architecture.decisions.decided())
    first_place_to_look = _first_place_to_look(architecture, registry)

    lines = [
        "# Runbook",
        "",
        "What you will see, what it means, and what to do. Failures here are "
        "grouped the way the evaluation harness classifies them, so a classified "
        "failure leads somewhere instead of sitting in a report.",
        "",
        "## When the answers are wrong and nothing is obviously broken",
        "",
        f"Look at **{first_place_to_look}** first. Quality flows one direction "
        f"through this system, and that component caps everything after it -- no "
        f"amount of work further along recovers what it lost.",
        "",
        f"Components in this system: {', '.join(f'`{c}`' for c in components)}.",
        "",
        "## By failure source",
        "",
    ]

    for source, (symptom, action) in SYMPTOMS.items():
        lines += [
            f"### {source}",
            "",
            f"**You see** — {symptom}",
            "",
            f"**Do** — {action}",
            "",
        ]

    if architecture.graph.sensitive_nodes():
        lines += [
            "## If data may have left the boundary",
            "",
            "**You see** — a component that handles regulated data appearing "
            "outside `in_boundary`, or an outward call from one.",
            "",
            "**Do** — stop the deployment before investigating. `app/boundary.py` "
            "checks at import, so a running system with this problem was started "
            "with the check removed. Establish what left and over what period "
            "before restarting anything; that question gets harder every hour.",
            "",
        ]

    return "\n".join(lines)


def _first_place_to_look(architecture, registry) -> str:
    """The earliest *decided* component whose quality bounds the rest.

    Restricted to what is actually in the system: the caps chain runs
    through components that may be undecided here, and a 3am instruction
    pointing at a module whose only content is a raise helps nobody.
    """
    decided = set(architecture.decisions.decided())
    fallback = min(decided) if decided else "the first step in app/pipeline.py"
    if registry is None:
        return "perception" if "perception" in decided else fallback
    candidates = [c for c in ("reasoning", "representation", "retrieval") if c in decided]
    if not candidates:
        return "perception" if "perception" in decided else fallback
    earliest = earliest_cap(candidates[0], registry.components)
    if earliest in decided:
        return earliest
    # Walk back down toward the decided part of the chain.
    return candidates[0]


# --- objectives ----------------------------------------------------------


UNSTATED_AVAILABILITY = (
    "<not stated> -- ask the sponsor; the spare count and the deploy story "
    "both hang on it"
)

AVAILABILITY_MEANS = {
    "always_on": "always on: a spare replica, and a deploy is not an outage",
    "business_hours": "business hours: planned windows outside them are free",
    "best_effort": "best effort: no spare, and that is a costed decision, not neglect",
}


def _slo(architecture) -> str:
    latency = _value(architecture, "latency_budget_ms")
    availability = _value(architecture, "availability_target")

    return "\n".join([
        "# Service objectives",
        "",
        "Two buckets, because reporting one is half a story. A technical number "
        "nobody outside the team cares about, and a business number nobody inside "
        "it can move directly -- and a system healthy on the first while the second "
        "does not move is a system nobody will renew.",
        "",
        "## Technical",
        "",
        f"- **Latency** — p95 under {latency or '<not stated>'}ms at expected peak. "
        f"Measured at the edge, not inside a component, because that is where "
        f"somebody experiences it.",
        f"- **Availability** — "
        f"{AVAILABILITY_MEANS.get(availability, UNSTATED_AVAILABILITY)}.",
        "- **Evaluation score** — the golden layer at or above the threshold CI "
        "gates on. A drop here is a regression whether or not anything is down.",
        "- **Adversarial score** — tracked separately and never averaged in. "
        "Scoring well on golden and badly on adversarial means nobody has "
        "attacked it yet.",
        "",
        "## Business",
        "",
        "- **The thing that should move** — stated by whoever asked for this, in "
        "their words, before it was built. If nobody can say what should change, "
        "that is the finding.",
        "",
        "## Baseline",
        "",
        "**Not captured.** Without one there is nothing to compare against, and "
        "any improvement claimed after launch is an assertion.",
        "",
        "Seven fields make a baseline usable: volume, cycle time per unit, labour "
        "hours, rework rate, exception rate, error rate, and the business metric "
        "itself. Two qualifiers do the real work — cycle time from a representative "
        "sample rather than the best case, and the whole thing **re-measurable by "
        "identical definitions in 60 days**. That last one is the test of whether "
        "you have a baseline or a number somebody said in a meeting.",
        "",
        "Where historical data is unreliable, measure prospectively for 30 to 60 "
        "days before deployment rather than accepting an estimate.",
        "",
    ])


# --- rollback ------------------------------------------------------------

ROLLBACK_STEPS = {
    "systemd-unit": (
        "sudo systemctl stop app\n"
        "sudo ln -sfn /opt/app-previous /opt/app\n"
        "sudo systemctl start app\n"
        "systemctl status app --no-pager\n"
    ),
    "compose": (
        "cd deploy\n"
        "docker compose down\n"
        "# pin the previous digest in compose.yaml, then\n"
        "docker compose up -d\n"
        "docker compose ps\n"
    ),
    "kubernetes-manifests": (
        "kubectl rollout undo deployment/app\n"
        "kubectl rollout status deployment/app --timeout=120s\n"
    ),
}


def _rollback(architecture) -> str:
    substrate = _approach(architecture, "deployment")
    steps = ROLLBACK_STEPS.get(substrate or "", "# no deployment substrate was decided\n")

    irreversible = _irreversible(architecture)
    return "\n".join([
        "# Rolling back",
        "",
        f"Substrate: **{substrate or 'not decided'}**",
        "",
        "```bash",
        steps.rstrip(),
        "```",
        "",
        "## What this does not undo",
        "",
        "Reverting a deployment restores the code. It does not reverse anything "
        "the running system already did. Everything below is irreversible by "
        "nature, and treating a rollback as though it covers them is how one "
        "incident becomes two.",
        "",
        *(
            [f"- {item}" for item in irreversible]
            or ["- Nothing in this system takes irreversible actions."]
        ),
        "",
        "Before rolling back, establish what the system did while the bad version "
        "was live. That question is easier to answer now than in an hour, and the "
        "audit trail is where the answer is.",
        "",
        "## Data",
        "",
        "A schema change applied forward is not undone by deploying the previous "
        "code. If this release migrated anything, the rollback is a migration of "
        "its own and needs writing before the release rather than during the "
        "incident.",
        "",
    ])


def _irreversible(architecture) -> list[str]:
    items = []
    if "integration" in architecture.decisions.decided():
        items.append(
            "**Outward calls already made.** Anything sent, charged, filed or "
            "written to another system stays done. The audit trail lists them."
        )
    if "memory" in architecture.decisions.decided():
        items.append(
            "**Anything promoted to long-term memory.** It will be recalled "
            "confidently by the previous version too."
        )
    if any(
        d.approach == "managed-api" for d in architecture.decisions.decided().values()
    ):
        items.append(
            "**Data sent to a vendor.** One-way by nature: it cannot be un-sent, "
            "and a rollback does not change what they now hold."
        )
    return items


# --- continuous integration ----------------------------------------------


def _ci(architecture, out: Path) -> None:
    workflows = out / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)

    boundary_step = ""
    if architecture.graph.sensitive_nodes():
        boundary_step = (
            "      # Importing this asserts placement. Data that may not leave\n"
            "      # cannot leave by construction, and a change that moves a\n"
            "      # sensitive component outside fails here rather than in review.\n"
            "      - name: Assert the boundary\n"
            "        run: python -c \"import app.boundary\"\n"
        )

    workflows.joinpath("ci.yml").write_text(
        "name: ci\n"
        "on: [push, pull_request]\n\n"
        "jobs:\n"
        "  check:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - uses: actions/setup-python@v5\n"
        '        with: {python-version: "3.11"}\n'
        "      - run: pip install -e .\n\n"
        f"{boundary_step}"
        "      # Gating on tests alone measures whether the code runs, not\n"
        "      # whether it is right. The evaluation is the one that says so --\n"
        "      # and it prints every layer, adversarial included, so scoring\n"
        "      # well on golden and badly on adversarial is visible in this\n"
        "      # step's own output rather than averaged away.\n"
        "      - name: Evaluate\n"
        "        run: python evals/harness.py --min-score 0.0\n"
    )


# --- helpers -------------------------------------------------------------


def _approach(architecture, component: str) -> str | None:
    decision = architecture.decisions.get(component)
    return decision.approach if decision else None


def _value(architecture, dimension: str):
    return architecture.values.get(dimension)
