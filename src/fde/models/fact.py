"""The single unit every input surface emits.

Prose, interviews, scans, sample pairs and asset inventories all reduce to facts.
Nothing downstream knows or cares which channel a fact arrived through.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from fde.models.base import Confidence, DimensionKind, Provenance
from fde.models.respondent import SYSTEM, Respondent


class Fact(BaseModel, frozen=True):
    dimension: str
    value: Any
    provenance: Provenance
    kind: DimensionKind = DimensionKind.REQUIREMENT
    confidence: Confidence = Confidence.MEDIUM
    respondent: Respondent = Field(default=SYSTEM)
    session_id: str | None = None

    # Where this came from, so a claim can be traced back to the sentence that made it.
    span: tuple[int, int] | None = None
    source: str | None = None

    def __init__(self, dimension: str, value: Any = None, provenance: Provenance = None, **kw):
        # Positional construction reads far better at call sites and in tests.
        super().__init__(dimension=dimension, value=value, provenance=provenance, **kw)
