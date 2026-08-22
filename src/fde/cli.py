"""The command line.

`fde kb validate` is strict by default because CI runs it, and a warning nobody
reads is not a check. `--lenient` exists for the hour when you are mid-way
through authoring content and the links do not resolve yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from fde.graph import find_gaps, validate_links
from fde.registry import RegistryError, load_registry

app = typer.Typer(help="Take an engagement from problem statement to a runnable project.")
kb = typer.Typer(help="Inspect the knowledge base in framework/.")
app.add_typer(kb, name="kb")

DEFAULT_ROOT = Path("framework")


@kb.command("validate")
def kb_validate(
    root: Annotated[Path, typer.Option(help="Registry directory.")] = DEFAULT_ROOT,
    lenient: Annotated[
        bool, typer.Option(help="Report dangling links without failing.")
    ] = False,
) -> None:
    """Check that everything parses and every cross-reference resolves."""
    try:
        registry = load_registry(root)
    except RegistryError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    errors = validate_links(registry)
    for error in errors:
        typer.echo(f"{error.source}: {error.message}", err=not lenient)

    counts = ", ".join(
        f"{len(getattr(registry, kind))} {kind}"
        for kind in ("approaches", "patterns", "stacks", "cases")
        if getattr(registry, kind)
    )
    typer.echo(f"loaded {counts or 'nothing'}")

    if errors and not lenient:
        typer.echo(f"{len(errors)} broken reference(s)", err=True)
        raise typer.Exit(1)


@kb.command("gaps")
def kb_gaps(
    root: Annotated[Path, typer.Option(help="Registry directory.")] = DEFAULT_ROOT,
) -> None:
    """Report what the corpus is missing. Work items, not errors -- always exits 0."""
    try:
        registry = load_registry(root)
    except RegistryError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    gaps = find_gaps(registry)
    for gap in gaps:
        typer.echo(f"{gap.kind}: {gap.detail}")
    typer.echo(f"{len(gaps)} gap(s)")


if __name__ == "__main__":  # pragma: no cover
    app()
