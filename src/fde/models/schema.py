"""The shapes registry content must satisfy.

Everything in `framework/` is data, validated against these models on load. The
validators here are opinionated on purpose -- each one encodes a way engagements
go wrong:

- A dimension without a value type turns "is this answer usable?" into a
  judgement call instead of a parse.
- A stack without a topology can be recommended into an environment it cannot
  run in.
- A pattern whose realizations satisfy different interfaces means swapping the
  library silently changes the architecture.
- A pattern with no no-framework option means the framework can never say
  "you do not need this library".
- An approach with no `avoid_when` has not been thought about.
- A ladder rung with no `graduate_when` leaves the framework defaulting to the
  most sophisticated option, which is the failure mode ladders exist to prevent.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from fde.models.base import DimensionKind, Evidence

NO_FRAMEWORK = "plain-python"


class ValueType(StrEnum):
    """What a legal answer for this dimension looks like.

    The follow-up mechanism parses an answer against this. "fast" is not a
    DURATION_MS, and detecting that needs no model.
    """

    DURATION_MS = "duration_ms"
    COUNT = "count"
    RATIO = "ratio"
    MONEY = "money"
    BOOLEAN = "boolean"
    ENUM = "enum"
    TEXT = "text"


class Maturity(StrEnum):
    STABLE = "stable"
    PARTIAL = "partial"
    NONE = "none"


class Dimension(BaseModel):
    """One axis of the problem space."""

    id: str
    type: ValueType
    kind: DimensionKind = DimensionKind.REQUIREMENT
    asks: str | None = None
    values: list[str] = Field(default_factory=list)

    # value -> {other_dimension: [values it removes]}
    prunes: dict[str, dict[str, list[str]]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_values(self) -> Dimension:
        if self.type is ValueType.ENUM and not self.values:
            raise ValueError(f"{self.id}: an enum dimension must declare its values")
        if self.type is not ValueType.ENUM and self.values:
            raise ValueError(f"{self.id}: only an enum dimension may declare values")
        for value in self.prunes:
            if value not in self.values:
                raise ValueError(f"{self.id}: prunes references undeclared value {value!r}")
        return self


class Stack(BaseModel):
    """A concrete tool. Churns in months, which is why it is not a pattern."""

    id: str
    name: str
    licence: str
    topologies: list[str] = Field(min_length=1)
    last_verified: date
    provides: dict[str, Maturity] = Field(default_factory=dict)
    supersedes: list[str] = Field(default_factory=list)
    evidence: Evidence | None = None


class Realization(BaseModel):
    """How one stack implements one pattern."""

    stack: str
    template: str
    provides: str  # the interface id this realization satisfies
    provenance: str | None = None


class Pattern(BaseModel):
    """A way of solving something. Stable for years."""

    id: str
    component: str
    realizations: list[Realization] = Field(min_length=1)
    applies_when: list[str] = Field(default_factory=list)
    avoid_when: list[str] = Field(default_factory=list)
    graduate_when: str | None = None
    evidence: Evidence | None = None

    @model_validator(mode="after")
    def _check_realizations(self) -> Pattern:
        interfaces = {r.provides for r in self.realizations}
        if len(interfaces) > 1:
            raise ValueError(
                f"{self.id}: every realization must satisfy the same interface, "
                f"got {sorted(interfaces)}"
            )
        stacks = {r.stack for r in self.realizations}
        if NO_FRAMEWORK not in stacks:
            raise ValueError(
                f"{self.id}: needs a {NO_FRAMEWORK!r} realization so the framework "
                f"can recommend no library at all"
            )
        return self


class Approach(BaseModel):
    """A class of solution: deterministic, classical ML, RAG, graph, solver..."""

    id: str
    name: str
    applies_when: list[str] = Field(min_length=1)
    avoid_when: list[str] = Field(default_factory=list)
    evidence: Evidence | None = None

    @model_validator(mode="after")
    def _check_avoid(self) -> Approach:
        if not self.avoid_when:
            raise ValueError(
                f"{self.id}: an approach must state avoid_when. One that always "
                f"applies has not been thought about."
            )
        return self


class Rung(BaseModel):
    """One step on a ladder. Cheapest first."""

    n: int
    id: str
    graduate_when: str | None = None
    cost: str | None = None
    needs: list[str] = Field(default_factory=list)


class Ladder(BaseModel):
    """An ordered set of options you earn your way rightward along."""

    id: str
    rungs: list[Rung] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_rungs(self) -> Ladder:
        expected = list(range(len(self.rungs)))
        if [r.n for r in self.rungs] != expected:
            raise ValueError(f"{self.id}: rungs must be contiguous from zero, got "
                             f"{[r.n for r in self.rungs]}")
        for rung in self.rungs[:-1]:
            if not rung.graduate_when:
                raise ValueError(
                    f"{self.id}: rung {rung.n} ({rung.id}) needs graduate_when -- "
                    f"without it the framework defaults to the most sophisticated rung"
                )
        return self


class Interface(BaseModel):
    """A typed slot contract. Realizations claim to satisfy one of these."""

    id: str
    methods: dict[str, str] = Field(default_factory=dict)
    description: str | None = None


class Component(BaseModel):
    """A part of a solution: ingestion, retrieval, reasoning, evaluation..."""

    id: str
    name: str
    required_when: list[str] = Field(default_factory=list)


class Case(BaseModel):
    """A real engagement, re-expressed. The corpus the framework learns from."""

    id: str
    profile: dict[str, Any] = Field(default_factory=dict)
    decisions: dict[str, str] = Field(default_factory=dict)
    outcome: str | None = None
    sanitization: str = "pending"
