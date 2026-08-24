"""A tiny predicate language for registry conditions.

Deliberately small: `always`, equality, inequality and numeric comparison. It
is parsed rather than evaluated, so a registry file can never execute anything,
and so a condition can be read by a person as easily as by the framework.

Two rules matter more than the grammar:

- **A predicate about something unknown is false, not an error.** Not knowing is
  the normal state during intake; the gates decide whether that is acceptable.
- **A predicate that cannot be read is an error, never false.** Silently false
  would drop a component and nobody would ever notice.
"""

from __future__ import annotations

import re

from fde.models.profile import Profile
from fde.registry import Registry

ALWAYS = "always"
COMPARISON = re.compile(r"^\s*(?P<left>\w+)\s*(?P<op>==|!=|>=|<=|>|<)\s*(?P<right>\S+)\s*$")
TRUTHY = re.compile(r"^\s*(?P<left>\w+)\s*$")

BOOLEANS = {"true": True, "false": False, "yes": True, "no": False}


class PredicateError(Exception):
    """A condition in the registry that cannot be read."""


def holds(predicate: str, profile: Profile, registry: Registry) -> bool:
    if predicate.strip() == ALWAYS:
        return True

    # Conjunction only, deliberately. Real conditions are usually "this and
    # that" -- nobody waiting *and* the volume is high. Adding `or` would let a
    # condition express two unrelated reasons as one, which is what avoid_when
    # lists already do, one line each, readably.
    if " and " in predicate:
        return all(holds(part, profile, registry) for part in predicate.split(" and "))

    match = COMPARISON.match(predicate) or TRUTHY.match(predicate)
    if not match:
        raise PredicateError(f"cannot read predicate {predicate!r}")

    dimension = match.group("left")
    if dimension not in registry.dimensions:
        raise PredicateError(f"predicate {predicate!r} names unknown dimension {dimension!r}")

    actual = profile.get(dimension)
    if actual is None:
        # Unknown is not false-because-we-checked; it is not-yet-known. Either
        # way this condition does not fire, and the gates report the gap.
        return False

    if "op" not in match.groupdict() or match.groupdict().get("op") is None:
        return bool(actual)

    return _compare(actual, match.group("op"), match.group("right"), predicate)


def _compare(actual, op: str, raw: str, predicate: str) -> bool:
    expected = _coerce(raw, actual)
    if op == "==":
        return actual == expected
    if op == "!=":
        return actual != expected
    if not isinstance(actual, int | float) or not isinstance(expected, int | float):
        raise PredicateError(f"cannot read predicate {predicate!r}: {op} needs numbers")
    return {">": actual > expected, "<": actual < expected,
            ">=": actual >= expected, "<=": actual <= expected}[op]


def _coerce(raw: str, alongside):
    """Read the right-hand side the way the left-hand value is written."""
    if isinstance(alongside, bool):
        return BOOLEANS.get(raw.lower(), raw)
    if isinstance(alongside, int | float):
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw
