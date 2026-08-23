"""Free-flow prose into facts.

Deterministic by design: registry vocabulary plus quantity patterns, and nothing
else. That keeps intake replayable, keeps it working inside an air gap, and keeps
"why did it decide that" answerable.

The bar is not how much it extracts. It is that it extracts **only what is
actually there**. A parser that guesses is worse than one that returns nothing,
because a wrong fact carries ARTIFACT provenance and will outrank the interview
answer that would have corrected it.
"""

from __future__ import annotations

import re
from typing import Any

from fde.models.base import DimensionKind, Provenance
from fde.models.fact import Fact
from fde.models.schema import Dimension, ValueType
from fde.registry import Registry

# "200,000", "2 million", "1.5k"
NUMBER = re.compile(
    r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<scale>k|m|bn|thousand|million|billion)?\b",
    re.I,
)
SCALES = {
    "k": 1_000, "thousand": 1_000,
    "m": 1_000_000, "million": 1_000_000,
    "bn": 1_000_000_000, "billion": 1_000_000_000,
}

DURATION = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>ms|milliseconds?|s|secs?|seconds?|min|minutes?)\b",
    re.I,
)
TO_MS = {
    "ms": 1, "millisecond": 1, "milliseconds": 1,
    "s": 1000, "sec": 1000, "secs": 1000, "second": 1000, "seconds": 1000,
    "min": 60_000, "minute": 60_000, "minutes": 60_000,
}

# How far either side of a number to look for the word that identifies it.
NEAR = 40


def parse_prose(
    text: str,
    registry: Registry,
    source: str | None = None,
    model: Any = None,  # noqa: ARG001 - reserved; P1 never calls one
) -> list[Fact]:
    """Read a brief into facts. `model` is accepted and ignored: an
    LLM-assisted parser is a later realization behind this same signature."""
    facts: list[Fact] = []
    for dimension in registry.dimensions.values():
        if dimension.type is ValueType.DURATION_MS:
            facts.extend(_read_duration(dimension, text, source))
        elif dimension.type not in (ValueType.COUNT, ValueType.RATIO, ValueType.MONEY):
            facts.extend(_read_vocabulary(dimension, text, source))

    facts.extend(_read_quantities(registry, text, source))
    return sorted(facts, key=lambda f: (f.span or (0, 0), f.dimension))


def _read_quantities(registry: Registry, text: str, source: str | None) -> list[Fact]:
    """Assign numbers to dimensions by proximity, competitively.

    "200,000 documents, 8,000 verified" holds two measurements a few characters
    apart. A window wide enough to find "verified" from the first number is wide
    enough to attach the wrong one, so every candidate pairing is scored by
    distance and each number goes to its nearest claimant -- and each dimension
    keeps only its best number.
    """
    quantitative = [
        d
        for d in registry.dimensions.values()
        if d.type in (ValueType.COUNT, ValueType.RATIO, ValueType.MONEY) and _near_words(d)
    ]
    if not quantitative:
        return []

    lowered = text.lower()
    candidates: list[tuple[int, str, re.Match]] = []
    for match in NUMBER.finditer(text):
        for dimension in quantitative:
            distance = _nearest_word_distance(lowered, match, _near_words(dimension))
            if distance is not None:
                candidates.append((distance, dimension.id, match))

    facts: list[Fact] = []
    claimed_numbers: set[tuple[int, int]] = set()
    claimed_dimensions: set[str] = set()
    for _distance, dimension_id, match in sorted(candidates, key=lambda c: (c[0], c[1])):
        if match.span() in claimed_numbers or dimension_id in claimed_dimensions:
            continue
        claimed_numbers.add(match.span())
        claimed_dimensions.add(dimension_id)
        facts.append(
            _fact(registry.dimensions[dimension_id], _scaled(match), match.span(), source)
        )
    return facts


def _nearest_word_distance(lowered: str, match: re.Match, words: list[str]) -> int | None:
    """Characters from the number to the closest word naming this dimension."""
    best: int | None = None
    for word in words:
        for found in re.finditer(rf"\b{re.escape(word)}\b", lowered):
            if found.start() >= match.end():
                distance = found.start() - match.end()
            elif found.end() <= match.start():
                distance = match.start() - found.end()
            else:
                distance = 0
            if distance <= NEAR and (best is None or distance < best):
                best = distance
    return best


def _scaled(match: re.Match) -> int:
    value = float(match.group("num").replace(",", ""))
    if scale := match.group("scale"):
        value *= SCALES[scale.lower()]
    return int(value)


def _read_vocabulary(dimension: Dimension, text: str, source: str | None) -> list[Fact]:
    """Match declared phrases. Phrases are anchored in the registry, not here,
    so recognising more is a content change rather than a code change."""
    lowered = text.lower()
    for value, phrases in _recognises(dimension).items():
        for phrase in phrases:
            at = lowered.find(phrase.lower())
            if at >= 0:
                return [
                    _fact(dimension, _typed(dimension, value), (at, at + len(phrase)), source)
                ]
    return []



def _read_duration(dimension: Dimension, text: str, source: str | None) -> list[Fact]:
    words = _near_words(dimension)
    lowered = text.lower()
    for match in DURATION.finditer(text):
        window = lowered[max(0, match.start() - NEAR) : match.end() + NEAR]
        if words and not any(re.search(rf"\b{re.escape(w)}\b", window) for w in words):
            continue
        unit = match.group("unit").lower().rstrip(".")
        millis = float(match.group("num")) * TO_MS.get(unit, TO_MS.get(unit.rstrip("s"), 1))
        return [_fact(dimension, int(millis), match.span(), source)]
    return []


def restate(facts: list[Fact], registry: Registry) -> str:
    """Play back what was understood, before designing anything.

    Said first on purpose: it is how an FDE discovers they misread the brief
    while that is still cheap.
    """
    if not facts:
        return "I understood nothing concrete from that. Tell me more, or answer a few questions."

    lines = ["Here is what I took from that:"]
    for fact in facts:
        dimension = registry.dimensions.get(fact.dimension)
        label = (dimension.asks if dimension and dimension.asks else fact.dimension).rstrip("?")
        lines.append(f"  - {label}: {_render(fact.value)}")
    lines.append("\nCorrect anything wrong before we go further.")
    return "\n".join(lines)


# --- helpers -------------------------------------------------------------


def _recognises(dimension: Dimension) -> dict[str, list[str]]:
    return getattr(dimension, "recognises", {}) or {}


def _near_words(dimension: Dimension) -> list[str]:
    return getattr(dimension, "recognises_near", []) or []


def _typed(dimension: Dimension, value: str) -> Any:
    if dimension.type is ValueType.BOOLEAN:
        return value.lower() in ("true", "yes")
    return value


def _fact(dimension: Dimension, value: Any, span: tuple[int, int], source: str | None) -> Fact:
    return Fact(
        dimension.id,
        value,
        Provenance.ARTIFACT,  # written down by the client, not inferred by us
        kind=dimension.kind or DimensionKind.REQUIREMENT,
        span=span,
        source=source,
    )


def _render(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return value.replace("_", " ").replace("-", " ")
    if isinstance(value, int) and value >= 1_000:
        return f"{value:,}"
    return str(value)
