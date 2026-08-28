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
# Word numbers two..twelve are read; "one" is deliberately not. It appears
# in prose that is not counting anything ("one operation", "one place"), and
# a brief that means the number one writes 1. Beyond twelve, people write
# digits.
WORD_NUMBERS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}
NUMBER = re.compile(
    r"(?P<num>\d[\d,]*(?:\.\d+)?|"
    + "|".join(WORD_NUMBERS)
    + r")\s*(?P<scale>k|m|bn|thousand|million|billion)?\b",
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

# Sentence ends. Crude, and enough: the point is only to stop a number in one
# sentence borrowing a word from the next.
SENTENCE = re.compile(r"(?<=[.!?])\s+")

# Cues that invert or qualify a matched phrase. A matcher cannot work out which
# value a negation selects, so on seeing one it declines rather than guesses.
NEGATIONS = re.compile(
    r"\b(not|never|no longer|untrue|false|isn't|is not|wasn't|doesn't|don't)\b", re.I
)
LOOKBACK = 60

# "between 8,000 and 12,000" is one quantity written two ways, not two
# measurements. Which end is meant is a question for a person.
RANGE = re.compile(r"\b(between|from)\b|\b\d[\d,]*\s*(?:-|--|to)\s*\d", re.I)


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

    # Confined to a sentence: a number in one sentence must not borrow the word
    # that names it from the next.
    candidates: list[tuple[int, str, re.Match]] = []
    for start, sentence in _sentences(text):
        if RANGE.search(sentence):
            continue  # one quantity written as two numbers; ask rather than guess
        lowered = sentence.lower()
        for match in NUMBER.finditer(sentence):
            for dimension in quantitative:
                distance = _nearest_word_distance(lowered, match, _near_words(dimension))
                if distance is not None:
                    candidates.append(
                        (distance, dimension.id, _shifted(match, start, text))
                    )

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


def _sentences(text: str) -> list[tuple[int, str]]:
    """Sentences with their offset into the original, so spans stay true."""
    out, at = [], 0
    for part in SENTENCE.split(text):
        out.append((text.index(part, at), part))
        at = out[-1][0] + len(part)
    return out


def _shifted(match: re.Match, offset: int, text: str) -> re.Match:
    """Re-find the match against the whole text, so the recorded span points
    into the document an FDE actually has in front of them."""
    return NUMBER.search(text, match.start() + offset, match.end() + offset) or match


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


def _numeric(raw: str) -> float:
    lowered = raw.lower()
    if lowered in WORD_NUMBERS:
        return float(WORD_NUMBERS[lowered])
    return float(raw.replace(",", ""))


def _scaled(match: re.Match) -> int:
    value = _numeric(match.group("num"))
    if scale := match.group("scale"):
        value *= SCALES[scale.lower()]
    return int(value)


def _read_vocabulary(dimension: Dimension, text: str, source: str | None) -> list[Fact]:
    """Match declared phrases, and decline when the match is not clean.

    Phrases live in the registry, so recognising more is a content change. What
    lives here is when *not* to trust a match: a negation nearby, or two values
    of the same dimension both present.
    """
    lowered = text.lower()
    hits: dict[str, tuple[int, int]] = {}

    for value, phrases in _recognises(dimension).items():
        for phrase in phrases:
            at = lowered.find(phrase.lower())
            if at < 0:
                continue
            if NEGATIONS.search(lowered[max(0, at - LOOKBACK) : at]):
                # Something inverts this. Which value it selects is beyond a
                # matcher, and the interview will ask.
                continue
            hits.setdefault(value, (at, at + len(phrase)))
            break

    hits = _most_specific(dimension, hits)

    # Two values that do not refine each other is a real requirement -- different
    # rules for different regions, say -- that the model cannot yet hold. Picking
    # one would hide it behind a confident answer.
    if len(hits) != 1:
        return []

    value, span = next(iter(hits.items()))
    return [_fact(dimension, _typed(dimension, value), span, source)]



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


def _most_specific(dimension: Dimension, hits: dict) -> dict:
    """Drop any value that a more precise co-occurring value refines.

    "Scanned supplier invoices" matches both scanned_documents and documents.
    That is one answer stated precisely, not two competing ones, and refusing it
    would send the framework asking what the brief already said.
    """
    refines = getattr(dimension, "refines", {}) or {}
    broader = {refines[v] for v in hits if v in refines}
    return {v: span for v, span in hits.items() if v not in broader}


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
