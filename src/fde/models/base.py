"""Shared value types: how a fact got here, and how strongly that counts."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class Provenance(StrEnum):
    """How a fact reached the profile."""

    DETECTED = "detected"  # measured off a machine
    ARTIFACT = "artifact"  # written down in a document the client owns
    INTERVIEW = "interview"  # said by a person
    OBSERVATION = "observation"  # watched during real work
    INFERRED = "inferred"  # the framework's own guess


class DimensionKind(StrEnum):
    """Which ordering applies to a dimension.

    Environment facts are measurable, so a measurement outranks anything said.
    Requirements are stated, so a document outranks a measurement -- you cannot
    detect a latency *budget*, only a latency.
    """

    ENVIRONMENT = "environment"
    REQUIREMENT = "requirement"


_ORDER: dict[DimensionKind, list[Provenance]] = {
    DimensionKind.ENVIRONMENT: [
        Provenance.DETECTED,
        Provenance.ARTIFACT,
        Provenance.INTERVIEW,
        Provenance.OBSERVATION,
        Provenance.INFERRED,
    ],
    DimensionKind.REQUIREMENT: [
        Provenance.ARTIFACT,
        Provenance.INTERVIEW,
        Provenance.DETECTED,
        Provenance.OBSERVATION,
        Provenance.INFERRED,
    ],
}


def wins(a: Provenance, b: Provenance, kind: DimensionKind) -> bool:
    """True if `a` should overwrite `b` for a dimension of this kind.

    Strictly ordered: a provenance never beats itself, which is what makes an
    equal-provenance restatement a correction rather than a conflict.
    """
    order = _ORDER[kind]
    return order.index(a) < order.index(b)


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Evidence(BaseModel):
    """Why the framework believes something, and when that belief was last checked."""

    case_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    last_verified: date | None = None
    verify_at_source: bool = False
    note: str | None = None


def says_something(text: object) -> bool:
    """Whether this is a sentence or an empty gesture.

    str.strip() removes ASCII whitespace and nothing else, so a zero-width
    space passes it -- which was once enough to satisfy the one gate the
    framework says cannot be worked around. Checked here, once, because the
    first fix landed at one call site and the same bypass stayed open at the
    other two.
    """
    return isinstance(text, str) and any(ch.isalnum() for ch in text)
