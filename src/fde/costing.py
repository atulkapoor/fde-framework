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
