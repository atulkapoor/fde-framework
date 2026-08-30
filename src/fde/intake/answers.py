"""Turning what someone said into a fact, or refusing to.

A dimension declares its type, which makes "is this answer usable?" a parse
rather than a judgement. "fast" is not a duration, and nothing needs to reason
about that -- it simply does not parse.

Refusing matters more than accepting. An unusable answer stored anyway becomes a
wrong fact at artifact strength, which then outranks the corrected answer that
arrives later. So a bad answer produces a **sharpening probe** naming the
precision that is missing, and nothing is recorded until it is supplied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fde.intake.prose import NEGATIONS, _most_specific
from fde.models.schema import Dimension, ValueType

SKIP = {"", "?", "idk", "unknown", "dont know", "don't know", "no idea", "skip", "pass"}

DURATION = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(ms|s|sec|secs|second|seconds|min|minutes?)?\s*$", re.I
)
TO_MS = {None: 1, "ms": 1, "s": 1000, "sec": 1000, "secs": 1000,
         "second": 1000, "seconds": 1000, "min": 60_000, "minute": 60_000, "minutes": 60_000}

SCALES = {"k": 1_000, "m": 1_000_000, "bn": 1_000_000_000}
COUNT = re.compile(r"^\s*(\d[\d,]*(?:\.\d+)?)\s*(k|m|bn)?\s*$", re.I)

TRUE = {"y", "yes", "true", "required", "must"}
FALSE = {"n", "no", "false", "not required", "optional"}


@dataclass(frozen=True)
class Answer:
    value: Any = None
    skipped: bool = False
    probe: str | None = None  # what to say when the answer was not usable

    @property
    def usable(self) -> bool:
        return not self.skipped and self.probe is None


def parse_answer(dimension: Dimension, raw: str) -> Answer:
    """Read one reply. Never guesses, and never stores what it could not read."""
    text = raw.strip()
    if text.lower() in SKIP:
        return Answer(skipped=True)

    if dimension.type is ValueType.ENUM:
        return _enum(dimension, text)
    if dimension.type is ValueType.DURATION_MS:
        return _duration(dimension, text)
    if dimension.type in (ValueType.COUNT, ValueType.MONEY):
        return _count(dimension, text)
    if dimension.type is ValueType.BOOLEAN:
        return _boolean(dimension, text)
    if dimension.type is ValueType.RATIO:
        return _ratio(dimension, text)
    return Answer(value=text)


def _enum(dimension: Dimension, text: str) -> Answer:
    lowered = text.lower()
    for value in dimension.values:
        if lowered == value.lower():
            return Answer(value=value)
    if dimension.multi_valued:
        parts = [p.strip() for chunk in lowered.split(",")
                 for p in chunk.split(" and ") if p.strip()]
        matched = []
        for part in parts:
            hit = _match_one(dimension, part)
            if hit is None:
                return Answer(probe=f"{part!r} is not one of: "
                                    f"{', '.join(dimension.values)}.")
            if hit not in matched:
                matched.append(hit)
        if matched:
            return Answer(value=tuple(matched) if len(matched) > 1 else matched[0])
    # Accept the way people actually talk, resolved the same way the prose
    # parser resolves it -- negation guard, most-specific value wins. A
    # first-match-wins loop here once recorded "on-prem with cloud burst" as
    # on-prem while fde frame read the identical words as hybrid: two intake
    # paths disagreeing on the registry's own vocabulary.
    hits: dict[str, tuple[int, int]] = {}
    for value, phrases in (dimension.recognises or {}).items():
        for phrase in phrases:
            at = lowered.find(phrase.lower())
            if at < 0:
                continue
            if NEGATIONS.search(lowered[:at]):
                continue
            hits.setdefault(value, (at, at + len(phrase)))
            break
    hits = _most_specific(dimension, hits)
    if len(hits) == 1:
        return Answer(value=next(iter(hits)))
    if len(hits) > 1:
        return Answer(probe=f"That could mean {' or '.join(sorted(hits))} -- which one?")
    return Answer(probe=f"I need one of: {', '.join(dimension.values)}.")


def _match_one(dimension: Dimension, part: str) -> str | None:
    """One comma-separated fragment against declared values, then phrases."""
    for value in dimension.values:
        if part == value.lower():
            return value
    for value, phrases in (dimension.recognises or {}).items():
        if any(phrase.lower() in part for phrase in phrases):
            return value
    return None


def _duration(dimension: Dimension, text: str) -> Answer:  # noqa: ARG001
    match = DURATION.match(text)
    if not match:
        return Answer(
            probe="I need a number of milliseconds -- at p95, under expected peak load. "
            "Something like 800ms or 2s."
        )
    unit = (match.group(2) or "").lower() or None
    return Answer(value=int(float(match.group(1)) * TO_MS[unit]))


def _count(dimension: Dimension, text: str) -> Answer:  # noqa: ARG001
    match = COUNT.match(text)
    if not match:
        return Answer(probe="I need a number. Something like 200000, 200,000 or 200k.")
    value = float(match.group(1).replace(",", ""))
    if scale := match.group(2):
        value *= SCALES[scale.lower()]
    return Answer(value=int(value))


def _boolean(dimension: Dimension, text: str) -> Answer:  # noqa: ARG001
    lowered = text.lower()
    if lowered in TRUE:
        return Answer(value=True)
    if lowered in FALSE:
        return Answer(value=False)
    return Answer(probe="I need yes or no.")


def _ratio(dimension: Dimension, text: str) -> Answer:  # noqa: ARG001
    try:
        value = float(text.rstrip("%").strip())
    except ValueError:
        return Answer(probe="I need a proportion, like 0.9 or 90%.")
    return Answer(value=value / 100 if "%" in text else value)
