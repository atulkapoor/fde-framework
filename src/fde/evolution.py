"""Capturing what an engagement taught.

**Capture now, revise later**, and the split is deliberate rather than lazy.
Rules cannot be revised until engagements have outcomes -- at engagement one
there are none, and at engagement fifty there are fifty points across dozens of
dimensions, which is nowhere near enough to fit anything. But a signal not
captured on the first engagement is gone, and the premise of the whole thing is
that it improves from use.

Three signals, and they are not worth the same.

**Overrides** are strong. The FDE was on site and chose differently, which is
information about the rule rather than about them -- so it is recorded with the
rule it overrode, never warned about, and never blocked.

**Trigger calibration** is strong for a specific reason: there is no
counterfactual. A trigger either fired when it was predicted to or it did not,
and both are observable. A trigger that never fires is an outcome too, which is
why they are swept rather than waited on.

**Replay** is weak and honestly so. Where the recommendation differs from what
was actually done, nobody knows what would have happened, and recording that as
a win would be fake rigour. It is marked unresolved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from statistics import median
from typing import Any

# A prediction landing within this of its horizon counts as well calibrated.
CALIBRATION_TOLERANCE_DAYS = 30

# Things that identify a client. Replaced before anything reaches the corpus,
# because a case nobody can publish is a case nobody contributes.
IDENTIFYING = re.compile(
    r"\b(ltd|limited|inc|llc|plc|gmbh|corp|corporation|bank|financial|services)\b", re.I
)


@dataclass
class Override:
    """The FDE chose differently. The most valuable signal there is."""

    component: str
    recommended: str
    chosen: str
    because: str
    overrode_rule: str
    conflicts_with: list[str] = field(default_factory=list)

    # Never warns, never blocks. The person on site knows things the rules do
    # not, and arguing with them teaches the framework nothing.
    blocking: bool = False


@dataclass
class Prediction:
    """A graduation trigger, with the claim it made and when it made it.

    Without the date and the horizon, "did it fire when we said?" is
    unanswerable -- and later is the only time anybody asks.
    """

    trigger: str
    condition: str
    predicted_at: str
    horizon_days: int


@dataclass
class Observation:
    trigger: str
    status: str  # fired | expired_unfired | pending
    condition: str
    predicted_at: str
    horizon_days: int
    observed_at: str | None = None
    measured: dict[str, Any] = field(default_factory=dict)

    @property
    def delta_days(self) -> int | None:
        """How long after the prediction it actually fired."""
        if not self.observed_at:
            return None
        return (_as_date(self.observed_at) - _as_date(self.predicted_at)).days

    @classmethod
    def fired(cls, prediction: Prediction, at: str, measured: dict[str, Any]) -> Observation:
        return cls(
            trigger=prediction.trigger, status="fired", condition=prediction.condition,
            predicted_at=prediction.predicted_at, horizon_days=prediction.horizon_days,
            observed_at=at, measured=measured,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "trigger": self.trigger,
            "status": self.status,
            "condition": self.condition,
            "predicted_at": self.predicted_at,
            "observed_at": self.observed_at,
            "delta_days": self.delta_days,
            "measured": self.measured,
        }


def sweep_triggers(
    predictions: list[Prediction], observations: list[Observation], today: str
) -> list[Observation]:
    """What happened to every prediction, including the ones nothing happened to.

    Silence is data. A trigger that never fires may be badly calibrated -- the
    threshold set too high, the condition describing something that does not
    occur -- and nobody finds out unless it is swept rather than waited on.
    """
    fired = {o.trigger: o for o in observations if o.status == "fired"}
    now = _as_date(today)

    swept = []
    for prediction in predictions:
        if prediction.trigger in fired:
            swept.append(fired[prediction.trigger])
            continue
        elapsed = (now - _as_date(prediction.predicted_at)).days
        swept.append(
            Observation(
                trigger=prediction.trigger,
                status="expired_unfired" if elapsed > prediction.horizon_days else "pending",
                condition=prediction.condition,
                predicted_at=prediction.predicted_at,
                horizon_days=prediction.horizon_days,
            )
        )
    return swept


def calibration(observations: list[Observation]) -> dict[str, Any]:
    """How good the predictions were.

    Strong evidence, and the reason is worth stating: there is no
    counterfactual here. A trigger fired when predicted or it did not, and both
    are things that happened rather than things anyone has to model.
    """
    fired = [o for o in observations if o.status == "fired"]
    expired = [o for o in observations if o.status == "expired_unfired"]
    deltas = [abs(o.delta_days - o.horizon_days) for o in fired if o.delta_days is not None]

    return {
        "strength": "strong",
        "why": "predicted against observed; nothing counterfactual to model",
        "fired": len(fired),
        "expired_unfired": len(expired),
        "median_delta_days": median(deltas) if deltas else 0,
        "well_calibrated": bool(deltas) and median(deltas) <= CALIBRATION_TOLERANCE_DAYS,
    }


def replay_verdict(recommended: str, actual: str) -> dict[str, Any]:
    """Whether replaying the rules agrees with what was done.

    Deliberately weak. Where they differ, the recommendation was not tried and
    nobody knows what would have happened -- so it is unresolved rather than a
    mark against either. Off-policy estimators exist for exactly this and are
    statistically fragile at the corpus sizes involved; using one here would be
    borrowing rigour rather than having it.
    """
    if recommended == actual:
        return {
            "verdict": "agreed",
            "strength": "weak",
            "why": "the rules reach what was actually done",
        }
    return {
        "verdict": "unresolved",
        "strength": "weak",
        "why": (
            f"recommended {recommended!r}, {actual!r} was done. The recommendation "
            f"was not tried, so nobody knows how it would have gone."
        ),
    }


def emit_case(
    engagement: str,
    profile: dict[str, Any],
    decisions: dict[str, str],
    observations: list[Observation],
    outcome: str,
    days: int | None = None,
    reused: list[str] | None = None,
    overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A finished engagement, in a shape the corpus can hold.

    Without this every engagement is a dead end and nothing compounds -- which
    is the difference between a framework that improves and a template that
    ages.
    """
    return {
        # Not the client's name. A case nobody can publish is a case nobody
        # contributes, and the shape is what carries the lesson anyway.
        "id": _anonymise(engagement),
        "profile": profile,
        "decisions": decisions,
        # Including the ones that were wrong. A corpus of successes teaches
        # less than one that admits what it got wrong, and the wrong ones are
        # what revision will eventually need.
        "triggers": [o.as_dict() for o in observations],
        # The strongest signal there is. A retrospective that loses the
        # overrides loses the exact thing revision will want first.
        "overrides": overrides or [],
        "outcome": outcome,
        "practice": {
            # The denominator improvement is measured against: is the Nth
            # solution faster than the first, and how much came off the shelf.
            "days": days,
            "reused": reused or [],
        },
        # Nobody has reviewed this yet, and saying otherwise would let an
        # unsanitised case claim the one property that gates publication.
        "sanitization": "pending",
    }


# --- helpers -------------------------------------------------------------


def _anonymise(name: str) -> str:
    """A stable, non-identifying handle."""
    import hashlib

    stripped = IDENTIFYING.sub("", name).strip()
    return "case-" + hashlib.sha256(stripped.lower().encode()).hexdigest()[:10]


def _as_date(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)
