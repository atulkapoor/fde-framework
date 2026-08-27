"""What has to be true before building is worth starting.

Five gates, and one of them is different from the rest.

Four block and accept an override with a recorded reason. An FDE on site can see
things a checklist cannot, and a framework that refuses to proceed on a
technicality gets worked around rather than used -- so the override is a
first-class move, and the reason lands in the risk section rather than in an
argument.

**Data access does not.** You can design around a missing baseline; you cannot
design around credentials you do not have. Waiting is the only move, and a
framework that lets an engagement proceed past this is helping somebody spend
three weeks designing against data they have never seen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fde.models.base import says_something
from fde.models.profile import Profile

# What makes a baseline usable. Fewer than these and a post-launch comparison
# is an assertion rather than a measurement.
BASELINE_FIELDS = (
    "volume",
    "cycle_time_per_unit_seconds",
    "labour_hours_per_week",
    "rework_rate",
    "exception_rate",
    "error_rate",
    "business_metric",
)

# Fallbacks for callers with no registry in hand. The registry is the source
# of truth -- dimensions declare `weight:` and `needs_judge:` in their own
# frontmatter, so a new decisive dimension arrives with its weight instead of
# waiting for an edit here that somebody forgets. These copies exist only so
# the gates still function bare, and they are expected to fall behind.
FALLBACK_DECISIVE = {
    "output_shape": 3.0,
    "data_residency": 3.0,
    "input_format": 2.0,
    "query_pattern": 2.0,
    "hosting": 2.0,
    "labelled_count": 2.0,
    "corpus_size": 1.5,
    "latency_budget_ms": 1.5,
    "interpretability_required": 1.5,
    "human_waiting": 1.0,
    "external_systems": 0.5,
    "recall_span": 0.5,
}

FALLBACK_NEEDS_A_JUDGE = {"output_shape": ["freeform"]}
FALLBACK_BOUNDARY = {"hosting": ["air-gapped", "on-prem"],
                     "data_residency": ["cannot_leave"]}


def _weights(registry) -> dict[str, float]:
    if registry is None or not getattr(registry, "dimensions", None):
        return FALLBACK_DECISIVE
    declared = {
        d.id: d.weight for d in registry.dimensions.values() if d.weight > 0
    }
    return declared or FALLBACK_DECISIVE


def _judged(registry) -> dict[str, list[str]]:
    if registry is None or not getattr(registry, "dimensions", None):
        return FALLBACK_NEEDS_A_JUDGE
    return {
        d.id: d.needs_judge for d in registry.dimensions.values() if d.needs_judge
    } or FALLBACK_NEEDS_A_JUDGE


def _boundary(registry) -> dict[str, list[str]]:
    if registry is None or not getattr(registry, "dimensions", None):
        return FALLBACK_BOUNDARY
    return {
        d.id: d.boundary_when
        for d in registry.dimensions.values() if d.boundary_when
    } or FALLBACK_BOUNDARY


# Dimensions the gates themselves consume. Named here so the registry's
# inert-dimension check can count gate usage as usage -- the same seam as
# graph.TOPOLOGY_DIMENSION: one declared join, not scattered string literals.
GATE_DIMENSIONS = {"licence_posture", "hosting", "output_shape", "data_residency"}

# The dimension the licence gate reads.
LICENCE_POSTURE = "licence_posture"


class HardGate(Exception):
    """This one cannot be overridden, and saying so is the point."""


@dataclass
class Result:
    ok: bool
    reason: str = ""


@dataclass
class Gate:
    name: str
    passed: bool
    reason: str = ""
    remedy: str = ""
    hard: bool = False


@dataclass
class Overridden:
    gate: str
    reason: str
    # What the gate said when this was granted. A waiver covers a stated
    # problem, not a gate name for the life of the engagement.
    against: str = ""


@dataclass
class Status:
    gates: list[Gate] = field(default_factory=list)
    known: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    assumed: list[str] = field(default_factory=list)
    missing_roles: list[str] = field(default_factory=list)
    overridden: list[Overridden] = field(default_factory=list)
    completeness: float = 0.0

    def gate(self, name: str) -> Gate:
        return next(g for g in self.gates if g.name == name)

    def override(self, name: str, reason: str, against: str | None = None) -> None:
        """Wave a blocking gate through, with the reason recorded.

        `against` is the gate's reason as it stood when the waiver was
        granted. Replaying a stored waiver passes what was stored; if the
        gate is now blocked for a *different* reason, the waiver does not
        cover it -- somebody agreed to a stated problem, not to the gate.
        """
        target = self.gate(name)
        if target.hard:
            raise HardGate(
                f"{name} cannot be overridden. {target.reason} Waiting is the only "
                f"move here, and designing against data nobody has seen is how "
                f"three weeks disappear."
            )
        if not says_something(reason):
            raise ValueError(
                f"overriding {name} needs a reason a person could read; a gate "
                f"waved through without one is a gate nobody considered"
            )
        if target.passed:
            raise ValueError(
                f"{name} is not blocking anything, so there is nothing to waive. "
                f"A waiver banked against a future problem is a waiver nobody "
                f"granted for the problem that actually arrives."
            )
        if against is not None and against.strip() != (target.reason or "").strip():
            # Not an error: the waiver simply does not apply here, and the
            # gate stays standing so somebody looks at what changed.
            return
        self.overridden.append(
            Overridden(gate=name, reason=reason, against=target.reason)
        )

    def blocked_by(self) -> list[str]:
        """Gates still standing in the way, after overrides.

        More useful than a single yes or no: an FDE wants to know which two
        things are outstanding, not that something is.
        """
        waved = {o.gate for o in self.overridden}
        return [g.name for g in self.gates if not g.passed and g.name not in waved]

    @property
    def can_proceed(self) -> bool:
        return not self.blocked_by()


def validate_baseline(baseline: dict[str, Any] | None) -> Result:
    """Whether this is a baseline or a number somebody said in a meeting.

    Two qualifiers do more work than the seven fields. Cycle time has to come
    from a representative sample rather than the best case -- the gap between
    what is possible and what happens is usually the whole project. And the
    definitions have to be recorded, because the test of a baseline is whether
    the same fields can be measured again in sixty days and compared.
    """
    if not baseline:
        return Result(False, "no baseline was captured")

    missing = [f for f in BASELINE_FIELDS if f not in baseline]
    if missing:
        return Result(False, f"missing: {', '.join(missing)}")

    if not baseline.get("sampled"):
        return Result(
            False,
            "cycle time must come from a representative sample, not the best case; "
            "the difference between what is possible and what happens is the project",
        )
    if not baseline.get("definitions_recorded"):
        return Result(
            False,
            "the definitions are not recorded, so this is not re-measurable in "
            "sixty days and nothing can be compared against it later",
        )
    return Result(True)


def completeness(profile: Profile, registry=None) -> float:
    """How much of what actually gets decided is settled.

    Weighted rather than counted. Answering ten incidental questions is not
    most of the way to a design, and a percentage built from field counts will
    say that it is. Weights come from the dimensions' own frontmatter.
    """
    weights = _weights(registry)
    total = sum(weights.values())
    have = sum(w for d, w in weights.items() if profile.resolved(d))
    return round(have / total, 3)


def input_status(
    profile: Profile,
    baseline: dict[str, Any] | None = None,
    data_access: bool | None = None,
    original_statement: str | None = None,
    current_statement: str | None = None,
    registry=None,
    licences: dict[str, str] | None = None,
) -> Status:
    """Known, assumed, missing -- and whether this is worth starting.

    `licences` is stack -> licence for the architecture as it would build
    now. Passed in rather than computed here, because only the caller knows
    whether an architecture exists yet; None means the licence gate has
    nothing to judge and stands open.
    """
    known = sorted(profile.values())
    contested = [d.dimension for d in profile.disagreements()]
    weights = _weights(registry)

    return Status(
        gates=[
            _data_access(data_access),
            _baseline(baseline),
            _client_readiness(profile),
            _scope_drift(original_statement, current_statement),
            _offline_evaluability(profile, registry),
            _licence_compatibility(profile, licences),
        ],
        known=known,
        missing=sorted(d for d in weights if not profile.resolved(d)),
        assumed=contested,
        missing_roles=_missing_roles(profile),
        completeness=completeness(profile, registry),
    )


# --- the gates -----------------------------------------------------------


def _data_access(data_access: bool | None) -> Gate:
    """The hard one.

    Everything else on this list can be worked around by an engineer who knows
    the domain. This cannot: without credentials there is nothing to look at,
    and a design built against imagined data is discovered to be wrong on the
    day the data arrives.
    """
    if data_access:
        return Gate("data_access", True, hard=True)
    return Gate(
        "data_access",
        False,
        reason="Credentials have not been shown to work against real data.",
        remedy="Get a connection that returns real rows, even a handful. "
               "Promised access is not access.",
        hard=True,
    )


def _baseline(baseline: dict[str, Any] | None) -> Gate:
    result = validate_baseline(baseline)
    if result.ok:
        return Gate("baseline_capture", True)
    return Gate(
        "baseline_capture",
        False,
        reason=result.reason,
        remedy=(
            "Measure volume, cycle time per unit, labour hours, rework rate, "
            "exception rate, error rate and the business metric, over 30 to 60 "
            "days, recording the definitions. Where history is unreliable, "
            "measure forward rather than accept an estimate."
        ),
    )


def _client_readiness(profile: Profile) -> Gate:
    """Whether anybody can say what good means.

    The eval owner is the scarcest person on an engagement and the one whose
    absence is discovered last, usually when somebody asks whether it is working
    and nobody can answer.
    """
    if "eval_owner" not in _missing_roles(profile):
        return Gate("client_readiness", True)
    return Gate(
        "client_readiness",
        False,
        reason="Nobody has been named who can say what separates acceptable "
               "from excellent.",
        remedy="Find the person whose judgement the client would accept about a "
               "borderline output. Without them nothing downstream is measurable.",
    )


def _scope_drift(original: str | None, current: str | None) -> Gate:
    """Measured against the first statement, always.

    Comparing against the latest version measures nothing: the whole point is
    the distance travelled from what was originally agreed.
    """
    if not original or not current or original.strip() == current.strip():
        return Gate("scope_drift", True)

    added = len(current.split()) - len(original.split())
    return Gate(
        "scope_drift",
        False,
        reason=f"The statement has moved from the original by roughly {abs(added)} "
               f"words. Drift is measured against the original, not the latest.",
        remedy="Either agree the new scope explicitly, or write down what was "
               "dropped to make room for it.",
    )


def _offline_evaluability(profile: Profile, registry=None) -> Gate:
    """Whether the metric can run where the system runs.

    An air-gapped deployment whose evaluation needs a hosted judge has no
    evaluation, and that is discovered at deployment when it is expensive.
    Both halves read the registry: which values place the engagement inside a
    boundary, and which output values need a model to judge them.
    """
    inside = any(
        profile.get(dimension) in values
        for dimension, values in _boundary(registry).items()
    )
    needs_judge = any(
        profile.get(dimension) in values
        for dimension, values in _judged(registry).items()
    )

    if not (inside and needs_judge):
        return Gate("offline_evaluability", True)
    return Gate(
        "offline_evaluability",
        False,
        reason="Freeform output needs a judge, and nothing may leave here.",
        remedy="Plan a judge that runs inside the boundary, and calibrate it "
               "against human agreement before quoting a number from it.",
    )


def _licence_compatibility(
    profile: Profile, licences: dict[str, str] | None
) -> Gate:
    """Whether the licence *combination* survives what the client intends.

    Each realization declares its licence; nothing used to check the
    aggregate. An FDE could hand a client shipping proprietary software a
    project pulling in an AGPL component -- a serious problem created by the
    framework, on the FDE's name. Judged at build time, against the stated
    posture, waivable only with a reason (which is what legal clearance is).
    """
    from fde.realization import copyleft

    tainted = {
        stack: licence
        for stack, licence in (licences or {}).items()
        if copyleft(licence)
    }
    if not tainted:
        return Gate("licence_compatibility", True)

    posture = profile.get(LICENCE_POSTURE)
    named = ", ".join(f"{stack} ({licence})" for stack, licence in sorted(tainted.items()))

    if posture == "open":
        return Gate("licence_compatibility", True)
    if posture == "internal_only":
        network = {s: l for s, l in tainted.items() if "AGPL" in l.upper()}
        if not network:
            return Gate("licence_compatibility", True)
        return Gate(
            "licence_compatibility",
            False,
            reason=f"Network copyleft in an internally served system: "
                   f"{', '.join(sorted(network))}. The AGPL triggers on serving, "
                   f"not distribution -- internal does not exempt it.",
            remedy="Swap the stack for a permissive alternative, or waive with "
                   "the legal clearance as the reason.",
        )
    if posture == "proprietary":
        return Gate(
            "licence_compatibility",
            False,
            reason=f"Copyleft components in a system the client ships as "
                   f"proprietary: {named}. Distribution obliges publishing "
                   f"changes, which is the one thing they cannot do.",
            remedy="Swap the stack for a permissive alternative, or waive with "
                   "the legal clearance as the reason.",
        )
    return Gate(
        "licence_compatibility",
        False,
        reason=f"Copyleft components are in this design ({named}) and nobody "
               f"has said what the client intends to do with the system.",
        remedy="Ask the sponsor: proprietary product, internal tool, or open "
               "source? The answer decides whether these licences are a "
               "problem at all.",
    )


def _missing_roles(profile: Profile) -> list[str]:
    spoken = {
        str(f.respondent.role)
        for dimension in profile.dimensions()
        for f in profile.history(dimension)
    }
    return sorted({"eval_owner", "admin"} - spoken)
