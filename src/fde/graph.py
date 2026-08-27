"""Cross-link resolution and gap detection over a loaded registry.

Two different questions:

- `validate_links` -- does everything this registry points at exist? A dangling
  reference is a bug, and it fails the build.
- `find_gaps` -- what is missing that nobody declared? A pattern nobody has
  evidence for, a stack nobody has checked in a year. These are work items, not
  errors, and they are how the corpus tells you where it is thin.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import BaseModel

from fde.predicate import referenced as _dimensions_in
from fde.registry import Registry

# The dimension whose answer becomes the deployment topology. Stacks declare
# which topologies they run in using this dimension's vocabulary, and the
# validator holds both sides to it.
TOPOLOGY_DIMENSION = "hosting"

# A stack unchecked for this long is a liability: tools churn in months.
STALE_AFTER_DAYS = 365


class LinkError(BaseModel):
    source: str  # which entry holds the bad reference
    message: str


class Gap(BaseModel):
    kind: str
    detail: str


def validate_links(registry: Registry) -> list[LinkError]:
    errors: list[LinkError] = []

    for pattern in registry.patterns.values():
        for case_id in _cited_cases(pattern):
            if case_id not in registry.cases:
                errors.append(
                    LinkError(
                        source=pattern.id,
                        message=f"pattern {pattern.id!r} cites unknown case {case_id!r}",
                    )
                )
        for realization in pattern.realizations:
            if realization.stack not in registry.stacks:
                errors.append(
                    LinkError(
                        source=pattern.id,
                        message=(
                            f"pattern {pattern.id!r} has a realization for unknown "
                            f"stack {realization.stack!r}"
                        ),
                    )
                )
            if registry.interfaces and realization.provides not in registry.interfaces:
                errors.append(
                    LinkError(
                        source=pattern.id,
                        message=(
                            f"pattern {pattern.id!r} claims unknown interface "
                            f"{realization.provides!r}"
                        ),
                    )
                )

    for approach in registry.approaches.values():
        for case_id in _cited_cases(approach):
            if case_id not in registry.cases:
                errors.append(
                    LinkError(
                        source=approach.id,
                        message=f"approach {approach.id!r} cites unknown case {case_id!r}",
                    )
                )

    for dimension in registry.dimensions.values():
        for value, pruned in dimension.prunes.items():
            for other in pruned:
                if registry.dimensions and other not in registry.dimensions:
                    errors.append(
                        LinkError(
                            source=dimension.id,
                            message=(
                                f"dimension {dimension.id!r} value {value!r} prunes "
                                f"unknown dimension {other!r}"
                            ),
                        )
                    )

    # Stacks and the topology dimension must speak one vocabulary. Two
    # spellings of the same place is how a legal answer to "where does this
    # run" once produced an architecture with zero realizations, silently.
    topology = registry.dimensions.get(TOPOLOGY_DIMENSION)
    if topology and topology.values:
        legal = set(topology.values)
        for stack in registry.stacks.values():
            for declared in stack.topologies:
                if declared not in legal:
                    errors.append(
                        LinkError(
                            source=stack.id,
                            message=(
                                f"stack {stack.id!r} declares topology {declared!r}, "
                                f"which is not a value of {TOPOLOGY_DIMENSION!r} "
                                f"({', '.join(topology.values)}) -- it can never be "
                                f"selected"
                            ),
                        )
                    )

    # A locale may pre-set values on dimensions that already exist; it may
    # never introduce one. Geography changes what you must produce, not how
    # you decide -- and this is the check that keeps that a rule rather
    # than a hope.
    for locale in registry.locales.values():
        for dimension, value in locale.presets.items():
            entry = registry.dimensions.get(dimension)
            if entry is None:
                errors.append(
                    LinkError(
                        source=locale.id,
                        message=(
                            f"locale {locale.id!r} presets unknown dimension "
                            f"{dimension!r} -- a locale may never introduce one"
                        ),
                    )
                )
            elif entry.values and value not in entry.values:
                errors.append(
                    LinkError(
                        source=locale.id,
                        message=(
                            f"locale {locale.id!r} presets {dimension}={value!r}, "
                            f"not one of: {', '.join(entry.values)}"
                        ),
                    )
                )

    return errors


def find_gaps(
    registry: Registry, today: str | date | None = None, templates: Path | None = None
) -> list[Gap]:
    now = _as_date(today) if today else date.today()
    gaps: list[Gap] = []

    # A realization pointing at a template nobody wrote resolves cleanly and
    # then emits a scaffold. That is honest but silent, so it is reported here
    # rather than discovered when someone reads the generated code.
    if templates and templates.exists():
        for pattern in registry.patterns.values():
            for realization in pattern.realizations:
                if not (templates / realization.template).exists():
                    gaps.append(
                        Gap(
                            kind="missing_template",
                            detail=(
                                f"{pattern.id} / {realization.stack}: "
                                f"{realization.template} is referenced and not written, "
                                f"so this emits a scaffold"
                            ),
                        )
                    )

    for pattern in registry.patterns.values():
        if not _cited_cases(pattern):
            gaps.append(
                Gap(
                    kind="pattern_without_evidence",
                    detail=f"{pattern.id}: recommended by nothing anyone has done",
                )
            )

    for stack in registry.stacks.values():
        age = (now - stack.last_verified).days
        if age > STALE_AFTER_DAYS:
            gaps.append(
                Gap(
                    kind="stale_stack",
                    detail=f"{stack.id}: last verified {age} days ago",
                )
            )

    serving: dict[str, int] = {}
    for approach in registry.approaches.values():
        for component in approach.components:
            serving[component] = serving.get(component, 0) + 1
    for component, count in serving.items():
        if count == 1:
            gaps.append(
                Gap(
                    kind="component_without_alternatives",
                    detail=f"{component}: only one approach serves it, so nothing is weighed",
                )
            )

    from fde.gates import GATE_DIMENSIONS

    acted_on: set[str] = set(GATE_DIMENSIONS)
    for approach in registry.approaches.values():
        for condition in [*approach.applies_when, *approach.avoid_when]:
            acted_on.update(_dimensions_in(condition))
    for component in registry.components.values():
        for condition in component.required_when:
            acted_on.update(_dimensions_in(condition))
    for dimension in registry.dimensions:
        if dimension not in acted_on:
            gaps.append(
                Gap(
                    kind="inert_dimension",
                    detail=(
                        f"{dimension}: asked about, but no decision depends on it -- "
                        f"a question whose answer changes nothing wastes the meeting"
                    ),
                )
            )

    # A dimension without a weight is invisible to completeness and to the
    # missing-questions list -- not wrong, just silently absent, which is the
    # failure mode weights-in-frontmatter were meant to end.
    for dimension in registry.dimensions.values():
        if dimension.weight <= 0:
            gaps.append(
                Gap(
                    kind="unweighted_dimension",
                    detail=(
                        f"{dimension.id}: no weight declared, so completeness "
                        f"ignores it and the interview never lists it as missing"
                    ),
                )
            )

    # Evidence has to point at something. A case with no profile, no decisions
    # and no outcome supports no claim, and a confidence rating that traces to
    # one is decoration -- reported per case, with how much leans on it.
    citations: dict[str, int] = {}
    for entry in [*registry.approaches.values(), *registry.patterns.values()]:
        for case_id in _cited_cases(entry):
            citations[case_id] = citations.get(case_id, 0) + 1
    for case_id, count in sorted(citations.items()):
        case = registry.cases.get(case_id)
        if case and not (case.profile or case.decisions or case.outcome):
            gaps.append(
                Gap(
                    kind="evidence_stub",
                    detail=(
                        f"{case_id}: cited {count} time(s) as evidence but records "
                        f"no profile, decisions or outcome -- every confidence "
                        f"that traces here is unsupported"
                    ),
                )
            )

    # Every legal answer to "where does this run" must leave at least one
    # stack standing, or that answer is a hollow deliverable waiting to happen.
    topology = registry.dimensions.get(TOPOLOGY_DIMENSION)
    if topology and registry.stacks:
        for value in topology.values:
            if not any(value in s.topologies for s in registry.stacks.values()):
                gaps.append(
                    Gap(
                        kind="unservable_topology",
                        detail=(
                            f"{value}: a legal answer to {TOPOLOGY_DIMENSION!r} "
                            f"that no stack can run in -- everything decided "
                            f"there is unrealizable"
                        ),
                    )
                )

    covered = {p.component for p in registry.patterns.values()}
    for component in registry.components:
        if component not in covered:
            gaps.append(
                Gap(kind="component_without_pattern", detail=f"{component}: no pattern offers it")
            )

    return gaps


def _cited_cases(entry: object) -> list[str]:
    evidence = getattr(entry, "evidence", None)
    return list(evidence.case_ids) if evidence else []


def _as_date(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def sweep_dead_zones(
    registry: Registry, samples: int = 300, seed: int = 0
) -> dict[str, object]:
    """Whether a fully specified engagement can actually be served.

    `find_gaps` checks that approaches exist per component; this checks that
    one can *fire*. The two disagree exactly where it hurts: a component with
    five approaches, all ruled out by the same combination of honest answers,
    counts as covered and is undecidable. Profiles are sampled inside the
    pruned space, so contradictory combinations the intake would never
    produce do not inflate the count.
    """
    import random

    from fde.decide import decide_all
    from fde.decompose import decompose
    from fde.models.base import Provenance
    from fde.models.fact import Fact
    from fde.models.profile import Profile
    from fde.space import Contradiction, Space

    pools: dict[str, list[object]] = {
        "count": [0, 10, 1_000, 200_000],
        "duration_ms": [50, 800, 5_000],
        "ratio": [0.5, 0.9, 0.99],
        "boolean": [True, False],
    }
    rng = random.Random(seed)
    dead: dict[str, dict[str, object]] = {}

    for _ in range(samples):
        space = Space.from_registry(registry)
        values: dict[str, object] = {}
        enum_dims = [d for d in registry.dimensions.values() if d.values]
        rng.shuffle(enum_dims)
        for dimension in enum_dims:
            surviving = sorted(space.surviving(dimension.id))
            # Pruning is not symmetric in the registry, so an answer that
            # looks legal can contradict an earlier one once it cascades.
            # Try the survivors in random order and keep the first that holds.
            for choice in rng.sample(surviving, len(surviving)):
                try:
                    space = space.answer(dimension.id, choice)
                except Contradiction:
                    continue
                values[dimension.id] = choice
                break
        for dimension in registry.dimensions.values():
            pool = pools.get(str(dimension.type))
            if pool and dimension.id not in values:
                values[dimension.id] = rng.choice(pool)

        profile = Profile()
        profile.ingest([
            Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()
        ])
        components = decompose(profile, registry)
        decisions = decide_all(
            values, registry, components=list(components.components)
        )
        for component, decision in decisions.items():
            if decision.approach is None:
                entry = dead.setdefault(
                    component, {"count": 0, "example": dict(values)}
                )
                entry["count"] = int(entry["count"]) + 1

    return {
        "samples": samples,
        "dead": {
            component: {
                "count": entry["count"],
                "rate": round(int(entry["count"]) / samples, 3),
                "example": entry["example"],
            }
            for component, entry in sorted(dead.items())
        },
    }
