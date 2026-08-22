"""Who said something.

Five roles, because different people know different things and are available at
different times. Questions are scoped to who can actually answer them, and two
respondents disagreeing is signal rather than noise.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class Role(StrEnum):
    SPONSOR = "sponsor"  # success criteria, budget, political constraints
    EVAL_OWNER = "eval_owner"  # what separates excellent from acceptable
    USER = "user"  # the real workflow, and its exceptions
    ADMIN = "admin"  # data access, audit, topology, entitlements
    SKEPTIC = "skeptic"  # why the last three attempts failed

    # Not a client role: the framework itself, for detected and inferred facts.
    SYSTEM = "system"


class Respondent(BaseModel, frozen=True):
    role: Role
    name: str | None = None

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.name} ({self.role.value})" if self.name else self.role.value


SYSTEM = Respondent(role=Role.SYSTEM)
