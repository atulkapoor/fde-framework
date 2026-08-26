"""Load `framework/` into a validated registry.

Content is markdown with YAML front matter: machine-readable head, human-readable
body. Both are kept -- the body is the rationale a person reads when they want to
know *why* a rule says what it says.

Error messages here are deliberately loud. A registry error surfaces at 3am on a
client site, and "invalid entry" would mean reading this loader to understand
your own typo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter
from pydantic import BaseModel, Field, ValidationError

from fde.models.schema import (
    Approach,
    Case,
    Component,
    Dimension,
    Interface,
    Ladder,
    Pattern,
    Stack,
)

# Directories that hold registry data but not registry entries. Declared rather
# than inferred, so a misspelled entry kind still fails loudly -- that guard is
# what stops content going silently missing.
NON_ENTRY_DIRS = {"templates"}


class RegistryError(Exception):
    """Something in framework/ is wrong, and this says which file and which field."""


# Directory name -> (model, attribute on Registry). The only place a new entry
# kind needs registering.
KINDS: dict[str, tuple[type[BaseModel], str]] = {
    "approaches": (Approach, "approaches"),
    "cases": (Case, "cases"),
    "components": (Component, "components"),
    "dimensions": (Dimension, "dimensions"),
    "interfaces": (Interface, "interfaces"),
    "ladders": (Ladder, "ladders"),
    "patterns": (Pattern, "patterns"),
    "stacks": (Stack, "stacks"),
}


class Registry(BaseModel):
    approaches: dict[str, Approach] = Field(default_factory=dict)
    cases: dict[str, Case] = Field(default_factory=dict)
    components: dict[str, Component] = Field(default_factory=dict)
    dimensions: dict[str, Dimension] = Field(default_factory=dict)
    interfaces: dict[str, Interface] = Field(default_factory=dict)
    ladders: dict[str, Ladder] = Field(default_factory=dict)
    patterns: dict[str, Pattern] = Field(default_factory=dict)
    stacks: dict[str, Stack] = Field(default_factory=dict)

    # (kind, id) -> the prose under the front matter
    bodies: dict[tuple[str, str], str] = Field(default_factory=dict)
    # (kind, id) -> the file it came from, for error messages
    files: dict[tuple[str, str], str] = Field(default_factory=dict)


def load_registry(root: str | Path) -> Registry:
    root = Path(root)
    if not root.exists():
        # Loudly, not as an empty registry: an empty registry decides nothing,
        # everything downstream "works", and the first sign is a hollow build.
        # The classic path here is running from the wrong directory.
        raise RegistryError(
            f"{root}: no registry here. Pass --registry pointing at a "
            f"registry directory (the framework/ of a source checkout)."
        )
    registry = Registry()

    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in NON_ENTRY_DIRS:
            continue
        if child.name not in KINDS:
            raise RegistryError(
                f"{child}: unknown registry directory {child.name!r}. "
                f"Expected one of: {', '.join(sorted(set(KINDS) | NON_ENTRY_DIRS))}. "
                f"A misspelled directory loads nothing and looks like missing content."
            )
        _load_kind(registry, child, child.name)

    return registry


def _load_kind(registry: Registry, directory: Path, kind: str) -> None:
    model, attribute = KINDS[kind]
    target: dict[str, Any] = getattr(registry, attribute)

    for path in sorted(directory.rglob("*.md")):
        head, body = _parse(path)
        entry = _validate(model, head, path)

        if entry.id != path.stem:
            raise RegistryError(
                f"{path}: id {entry.id!r} disagrees with filename {path.stem!r}. "
                f"Cross-links resolve by id, so drift makes entries unfindable."
            )
        if entry.id in target:
            raise RegistryError(
                f"{path}: duplicate id {entry.id!r}, already defined in "
                f"{registry.files[(kind, entry.id)]}"
            )

        target[entry.id] = entry
        registry.bodies[(kind, entry.id)] = body
        registry.files[(kind, entry.id)] = str(path)


def _parse(path: Path) -> tuple[dict[str, Any], str]:
    post = frontmatter.load(path)
    if not post.metadata:
        raise RegistryError(
            f"{path}: no YAML front matter. Registry entries need a '---' delimited "
            f"head; the prose below it is kept as the rationale."
        )
    return post.metadata, post.content


def _validate(model: type[BaseModel], head: dict[str, Any], path: Path) -> Any:
    try:
        return model(**head)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '<entry>'}: {err['msg']}"
            for err in exc.errors()
        )
        raise RegistryError(f"{path}: {problems}") from exc
