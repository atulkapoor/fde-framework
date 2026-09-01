"""What it costs, with the date attached.

Every absolute here ages. Prices fall, hardware changes, and a figure quoted in
a proposal a year after it was written is wrong in a way nobody notices -- so
each carries the date it was true and the rule for working it out again.

The sizing is the part usually got wrong. Counting weights against average
throughput understates a fleet substantially, because redundancy, peak and
prefill overhead each multiply it, and the understatement is discovered in
production rather than in the spreadsheet.

Both conclusions live here on purpose. At sustained interactive volume,
self-hosting loses to a managed endpoint; on bursty batch work it wins by a wide
margin. A framework that only knew one of them would be wrong half the time, and
confidently.
"""

from __future__ import annotations

import math
import warnings
from datetime import date
from typing import Any

from fde.scan import GPU, Hardware, fits

# Every figure below was true on this date and will not stay true.
AS_OF = "2026-08"
STALE_AFTER_DAYS = 270

# Indicative. Re-derive against current pricing rather than quoting these.
GPU_COST_PER_HOUR = 4.50
MANAGED_COST_PER_MILLION_TOKENS = 3.00
TOKENS_PER_REQUEST = 1_500

# The unit being rented. A replica is however many of these the model needs,
# which is the step usually skipped -- a 70B model in bf16 is 140GB of weights
# and does not run on one of them.
CARD_VRAM_GB = 80

# Traffic does not arrive evenly. Sizing to the daily mean leaves a fleet that
# fails at the busiest hour, which is the hour anybody notices.
PEAK_MULTIPLIER = 2.0

# One spare. A fleet with no redundancy is a fleet that is down during a deploy.
REDUNDANCY = 1.34

# Prefill is compute-bound and does not batch as well as decode, so a fleet
# sized on decode throughput alone is short.
PREFILL_OVERHEAD = 1.2

HOURS_PER_MONTH = 730


def gpus_per_replica(params_b: float, precision: str = "bf16") -> int:
    """How many cards one copy of this model occupies.

    Sizing in replicas and pricing each as one GPU is how a fleet is quoted at
    a third of its cost. A replica is a number of cards, and the number comes
    from the weights plus the cache rather than from the weights alone.
    """
    one_card = Hardware(gpus=[GPU("card", vram_gb=CARD_VRAM_GB)])
    fit = fits(one_card, params_b, precision=precision)
    return max(1, math.ceil(fit.required_gb / fit.available_gb))


def size_for(
    requests_per_day: int,
    params_b: float,
    requests_per_second_per_replica: float = 2.0,
    today: str | None = None,
) -> dict[str, Any]:
    """How many replicas this actually needs, and how many cards that is.

    The naive figure is reported beside the real one, because the gap is the
    finding -- and somebody will otherwise arrive at the naive figure
    independently and wonder why the estimate is higher.
    """
    _warn_if_stale(today)

    mean_rps = requests_per_day / 86_400
    naive = max(1, round(mean_rps / requests_per_second_per_replica))
    real = max(
        1,
        round(
            (mean_rps * PEAK_MULTIPLIER * PREFILL_OVERHEAD * REDUNDANCY)
            / requests_per_second_per_replica
        ),
    )
    per_replica = gpus_per_replica(params_b)

    return {
        "naive_replicas": naive,
        "replicas": real,
        "gpus_per_replica": per_replica,
        "gpus": real * per_replica,
        "factors": {
            "peak": f"traffic is not flat; sized at {PEAK_MULTIPLIER}x the daily mean",
            "prefill": f"prefill is compute-bound and batches worse than decode "
                       f"({PREFILL_OVERHEAD}x)",
            "redundancy": "one spare, so a deploy is not an outage",
            "model_size": f"a {params_b:g}B model at bf16 occupies {per_replica} "
                          f"card(s) per replica, weights and cache together",
        },
        "monthly_cost": round(
            real * per_replica * GPU_COST_PER_HOUR * HOURS_PER_MONTH, 2
        ),
        "as_of": AS_OF,
        "rederive": (
            "measure requests per second per replica on the real model and "
            "hardware, then apply peak, prefill and redundancy to the measured "
            "figure rather than to this one"
        ),
    }


def compare_hosting(
    requests_per_day: int,
    params_b: float,
    human_waiting: bool = True,
    today: str | None = None,
) -> dict[str, Any]:
    """Managed against self-hosted, for this workload.

    The answer flips on utilisation and on whether anybody is waiting, which is
    why the question cannot be settled once and quoted forever. Sustained
    interactive traffic keeps a self-hosted fleet running around the clock;
    bursty batch work pays for nothing between jobs.
    """
    _warn_if_stale(today)

    tokens_per_month = requests_per_day * 30 * TOKENS_PER_REQUEST
    managed = tokens_per_month / 1e6 * MANAGED_COST_PER_MILLION_TOKENS

    per_replica = gpus_per_replica(params_b)

    if human_waiting:
        # Somebody is waiting, so the fleet stays up whether or not it is busy,
        # sized for the peak hour and carrying a spare.
        plan = size_for(requests_per_day, params_b, today=today)
        self_hosted = plan["monthly_cost"]
        note = (
            f"Sustained interactive traffic keeps this running around the clock "
            f"at {plan['gpus']} cards ({per_replica} per replica), and redundancy "
            f"and peak headroom are most of the bill."
        )
    else:
        # Nobody waiting, so a cold start costs nothing and idle time is avoidable.
        busy_hours = (requests_per_day * 30) / (2.0 * 3600)
        self_hosted = busy_hours * per_replica * GPU_COST_PER_HOUR
        plan = {"replicas": 1}
        note = (
            "Nobody is waiting, so this scales to zero between jobs and pays for "
            "compute rather than for availability."
        )

    return {
        "managed_monthly": round(managed, 2),
        "self_hosted_monthly": round(self_hosted, 2),
        "replicas": plan["replicas"],
        "gpus_per_replica": per_replica,
        "recommendation": "managed" if managed < self_hosted else "self-hosted",
        "why": note,
        "as_of": AS_OF,
        "rederive": (
            "check current per-token and per-hour pricing, and measure tokens "
            "per request on real traffic rather than assuming"
        ),
    }


def effort_by_analogy(profile: dict[str, Any], cases: dict[str, Any]) -> dict[str, Any]:
    """How long this took the last time something like it was done.

    An estimate from comparable work, with the comparables named so somebody
    can disagree with the comparison rather than with the number.
    """
    analogues = [
        case_id for case_id, case in cases.items()
        if _overlap(profile, getattr(case, "profile", {})) >= 2
    ]
    if not analogues:
        return {
            "analogues": [],
            "range_weeks": None,
            "why": "nothing in the corpus resembles this closely enough to "
                   "estimate from. An estimate without a comparable is a guess "
                   "with a number on it.",
        }
    return {
        "analogues": sorted(analogues),
        "range_weeks": (3, 8),
        "why": f"estimated from {len(analogues)} comparable engagement(s); "
               f"disagree with the comparison rather than with the number",
        "as_of": AS_OF,
    }


def _overlap(profile: dict[str, Any], other: dict[str, Any]) -> int:
    return sum(1 for k, v in profile.items() if other.get(k) == v)


def _warn_if_stale(today: str | None) -> None:
    """Say so when these figures have aged past usefulness."""
    if not today:
        return
    age = (date.fromisoformat(today) - date.fromisoformat(f"{AS_OF}-01")).days
    if age > STALE_AFTER_DAYS:
        warnings.warn(
            f"these figures are as of {AS_OF}, roughly {age} days ago. Pricing and "
            f"hardware have moved; re-derive before quoting them.",
            UserWarning,
            stacklevel=3,
        )


# --- unit economics: the arbitrage-trap check -------------------------------

WORKDAYS_PER_MONTH = 22

# Reused prompt prefixes bill at roughly a tenth of the input rate on the
# hosted APIs that support prompt caching. Dated like every figure here.
CACHED_PREFIX_DISCOUNT = 0.10


def unit_economics(
    workflows_per_day: float,
    price_per_seat_month: float,
    steps_per_workflow: int = 5,
    tokens_per_step: int = TOKENS_PER_REQUEST,
    cheap_path_coverage: float | None = None,
    cached_prefix_share: float = 0.0,
    today: str | None = None,
) -> dict:
    """Whether a seat earns more than it burns, and which lever moves it.

    The failure this exists to name: a per-seat price set before anyone
    multiplied cost-per-workflow by workflows-per-day by workdays. A margin
    that collapses the moment users actually adopt the product is not a
    pricing problem, it is an architecture bill arriving late -- and the
    three levers below are the same decisions this corpus already makes:
    a cheap deterministic path in front of the model (cascade), cached
    prompt prefixes, and a bounded loop.
    """
    _warn_if_stale(today)

    for name, fraction in (("cheap_path_coverage", cheap_path_coverage),
                           ("cached_prefix_share", cached_prefix_share)):
        if fraction is not None and not 0.0 <= fraction <= 1.0:
            raise ValueError(
                f"{name} is a fraction between 0 and 1, got {fraction!r} -- "
                f"if that was a percentage, divide by 100. A share above one "
                f"turns the seat cost negative and reports a bogus healthy "
                f"margin, which is the exact failure this check exists to name."
            )

    def seat_cost(steps: int, coverage: float, cached: float) -> float:
        model_workflows = workflows_per_day * (1.0 - coverage)
        tokens = model_workflows * steps * tokens_per_step
        effective = tokens * ((1.0 - cached) + cached * CACHED_PREFIX_DISCOUNT)
        return effective / 1e6 * MANAGED_COST_PER_MILLION_TOKENS * WORKDAYS_PER_MONTH

    coverage = cheap_path_coverage or 0.0
    cost = seat_cost(steps_per_workflow, coverage, cached_prefix_share)
    margin = price_per_seat_month - cost

    levers = []
    if coverage < 0.5:
        levers.append((
            "route the measurable share to rules first (cascade at 50% coverage)",
            price_per_seat_month - seat_cost(steps_per_workflow, 0.5, cached_prefix_share),
        ))
    if cached_prefix_share < 0.7:
        levers.append((
            "cache the shared prefix (70% of tokens at the cached rate)",
            price_per_seat_month - seat_cost(steps_per_workflow, coverage, 0.7),
        ))
    if steps_per_workflow > 3:
        levers.append((
            "bound the loop at 3 steps (the cap the posture section documents)",
            price_per_seat_month - seat_cost(3, coverage, cached_prefix_share),
        ))

    return {
        "cost_per_workflow": round(cost / (workflows_per_day * WORKDAYS_PER_MONTH), 4)
        if workflows_per_day else 0.0,
        "cost_per_seat_month": round(cost, 2),
        "price_per_seat_month": price_per_seat_month,
        "margin_per_seat": round(margin, 2),
        "underwater": margin <= 0,
        "levers": [(reason, round(new_margin, 2)) for reason, new_margin in levers],
    }
