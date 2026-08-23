"""The command line.

`fde kb validate` is strict by default because CI runs it, and a warning nobody
reads is not a check. `--lenient` exists for the hour when you are mid-way
through authoring content and the links do not resolve yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from fde.factlog import load_engagement, start_engagement
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


@app.command("start")
def start(
    name: Annotated[str, typer.Argument(help="Engagement name.")],
    base: Annotated[Path, typer.Option(help="Where engagements live.")] = Path("engagements"),
    statement: Annotated[
        str | None, typer.Option(help="The problem, in prose. Optional.")
    ] = None,
) -> None:
    """Begin an engagement.

    A statement is optional: an FDE who only answers questions is a supported
    path, and so is pasting prose later.
    """
    try:
        engagement = start_engagement(base, name, statement=statement)
    except FileExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"started {engagement.root}")
    typer.echo("  facts/      one file per session, append-only")
    typer.echo("  artifacts/  drop specs, schemas and sample pairs here")
    if not statement:
        typer.echo("\nNo statement yet. Add prose later, or start answering questions.")


@app.command("status")
def status(
    root: Annotated[Path, typer.Argument(help="The engagement directory.")],
) -> None:
    """What is known, what is contested, and who said it."""
    engagement = load_engagement(root)
    profile = engagement.profile

    if profile.is_empty():
        typer.echo("nothing recorded yet")
        return

    resolved = profile.values()
    if resolved:
        typer.echo(f"known ({len(resolved)})")
        for dimension in sorted(resolved):
            fact = profile.fact(dimension)
            typer.echo(f"  {dimension} = {fact.value}   [{_who(fact)}]")

    # Disagreement is the most valuable thing discovery produces. It goes last so
    # it is the final thing on screen, and it is never summarised away.
    disagreements = profile.disagreements()
    if disagreements:
        typer.echo(f"\nunresolved -- respondents disagree ({len(disagreements)})")
        for d in disagreements:
            typer.echo(f"  {d.dimension}")
            for fact in d.facts:
                typer.echo(f"    {_who(fact)} says {fact.value}")


def _who(fact) -> str:
    """Name and role together.

    The role is not decoration: it is what tells an FDE whose answer to weigh
    for which dimension. A sponsor on latency and a user on latency are
    different kinds of claim.
    """
    role = str(fact.respondent.role)
    name = fact.respondent.name
    return f"{name}, {role}" if name else role


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
