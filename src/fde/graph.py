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

from pydantic import BaseModel

from fde.registry import Registry

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

    return errors


def find_gaps(registry: Registry, today: str | date | None = None) -> list[Gap]:
    now = _as_date(today) if today else date.today()
    gaps: list[Gap] = []

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

    acted_on: set[str] = set()
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

    covered = {p.component for p in registry.patterns.values()}
    for component in registry.components:
        if component not in covered:
            gaps.append(
                Gap(kind="component_without_pattern", detail=f"{component}: no pattern offers it")
            )

    return gaps


def _dimensions_in(condition: str) -> set[str]:
    """The dimensions a predicate reads."""
    return {
        part.split()[0]
        for part in condition.split(" and ")
        if part.split() and part.split()[0] != "always"
    }


def _cited_cases(entry: object) -> list[str]:
    evidence = getattr(entry, "evidence", None)
    return list(evidence.case_ids) if evidence else []


def _as_date(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)
